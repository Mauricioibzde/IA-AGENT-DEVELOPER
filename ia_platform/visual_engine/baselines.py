"""Visual baselines — approve/reject goldens for multi-route regression (Phase 7)."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,119}$")
BASELINE_FILE = "baseline.png"
META_FILE = "meta.json"


def baselines_root(artifacts_root: Path) -> Path:
    root = Path(artifacts_root).resolve() / "baselines"
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_route_id(route_id: str) -> str:
    rid = str(route_id or "").strip().replace("\\", "/").strip("/")
    # Allow nested logical routes as flat ids: home/index → home__index
    rid = rid.replace("/", "__")
    if not ROUTE_ID_RE.match(rid):
        raise ValueError(
            "invalid route_id (use letters, digits, . _ - ; max 120 chars)"
        )
    if rid in {".", ".."} or ".." in rid:
        raise ValueError("invalid route_id")
    return rid


def baseline_dir(artifacts_root: Path, route_id: str) -> Path:
    rid = sanitize_route_id(route_id)
    root = baselines_root(artifacts_root)
    path = (root / rid).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escape") from exc
    return path


def list_baselines(artifacts_root: Path) -> List[Dict[str, Any]]:
    root = baselines_root(artifacts_root)
    items: List[Dict[str, Any]] = []
    if not root.is_dir():
        return items
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        meta = _read_meta(child)
        png = child / BASELINE_FILE
        if not png.is_file() and not meta:
            continue
        items.append(
            {
                "routeId": child.name,
                "status": meta.get("status") or ("approved" if png.is_file() else "empty"),
                "hasBaseline": png.is_file(),
                "path": f".agent/visual/baselines/{child.name}/{BASELINE_FILE}",
                "viewport": meta.get("viewport") or {},
                "sourceComparisonId": meta.get("sourceComparisonId"),
                "label": meta.get("label") or child.name,
                "updatedAt": meta.get("updatedAt"),
                "createdAt": meta.get("createdAt"),
                "notes": meta.get("notes") or "",
            }
        )
    return items


def get_baseline(artifacts_root: Path, route_id: str) -> Optional[Dict[str, Any]]:
    try:
        directory = baseline_dir(artifacts_root, route_id)
    except ValueError:
        return None
    if not directory.is_dir():
        return None
    meta = _read_meta(directory)
    png = directory / BASELINE_FILE
    if not png.is_file() and not meta:
        return None
    return {
        "routeId": sanitize_route_id(route_id),
        "status": meta.get("status") or ("approved" if png.is_file() else "empty"),
        "hasBaseline": png.is_file(),
        "path": f".agent/visual/baselines/{sanitize_route_id(route_id)}/{BASELINE_FILE}",
        "absolutePath": str(png) if png.is_file() else None,
        "viewport": meta.get("viewport") or {},
        "sourceComparisonId": meta.get("sourceComparisonId"),
        "label": meta.get("label") or sanitize_route_id(route_id),
        "updatedAt": meta.get("updatedAt"),
        "createdAt": meta.get("createdAt"),
        "notes": meta.get("notes") or "",
        "meta": meta,
    }


def approve_baseline(
    artifacts_root: Path,
    *,
    route_id: str,
    source_png: Path,
    comparison_id: str = "",
    viewport: Optional[Dict[str, Any]] = None,
    label: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Promote an actual/reference PNG to the golden baseline for a route."""
    source_png = Path(source_png).resolve()
    if not source_png.is_file():
        raise FileNotFoundError(f"source image not found: {source_png}")
    directory = baseline_dir(artifacts_root, route_id)
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / BASELINE_FILE
    prev = _read_meta(directory)
    shutil.copy2(source_png, dest)
    now = time.time()
    meta = {
        "routeId": sanitize_route_id(route_id),
        "status": "approved",
        "label": (label or prev.get("label") or sanitize_route_id(route_id)).strip(),
        "notes": notes if notes is not None else prev.get("notes") or "",
        "sourceComparisonId": comparison_id or prev.get("sourceComparisonId") or "",
        "viewport": viewport or prev.get("viewport") or {},
        "createdAt": prev.get("createdAt") or now,
        "updatedAt": now,
        "approvedAt": now,
    }
    _write_meta(directory, meta)
    return get_baseline(artifacts_root, route_id) or meta


def reject_baseline(
    artifacts_root: Path,
    *,
    route_id: str,
    comparison_id: str = "",
    notes: str = "",
    remove_image: bool = False,
) -> Dict[str, Any]:
    """Mark route baseline as rejected (do not promote). Optionally remove golden."""
    directory = baseline_dir(artifacts_root, route_id)
    directory.mkdir(parents=True, exist_ok=True)
    prev = _read_meta(directory)
    now = time.time()
    if remove_image:
        png = directory / BASELINE_FILE
        if png.is_file():
            png.unlink()
    meta = {
        **prev,
        "routeId": sanitize_route_id(route_id),
        "status": "rejected",
        "notes": notes if notes else prev.get("notes") or "",
        "lastRejectedComparisonId": comparison_id or "",
        "createdAt": prev.get("createdAt") or now,
        "updatedAt": now,
        "rejectedAt": now,
    }
    _write_meta(directory, meta)
    return get_baseline(artifacts_root, route_id) or meta


def delete_baseline(artifacts_root: Path, route_id: str) -> bool:
    directory = baseline_dir(artifacts_root, route_id)
    if not directory.exists():
        return False
    shutil.rmtree(directory, ignore_errors=True)
    return not directory.exists()


def resolve_baseline_image(artifacts_root: Path, route_id: str) -> Path:
    info = get_baseline(artifacts_root, route_id)
    if not info or not info.get("hasBaseline"):
        raise FileNotFoundError(f"no approved baseline for route: {route_id}")
    path = Path(info["absolutePath"])
    if not path.is_file():
        raise FileNotFoundError(f"baseline image missing for route: {route_id}")
    return path


def find_comparison_actual(
    artifacts_root: Path,
    comparison_id: str,
    *,
    prefer: str = "actual",
) -> Path:
    """Locate PNG to promote from a comparison folder."""
    cid = str(comparison_id or "").strip()
    if not cid or "/" in cid or "\\" in cid or ".." in cid:
        raise ValueError("invalid comparison id")
    root = Path(artifacts_root).resolve()
    folder = (root / cid).resolve()
    try:
        folder.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escape") from exc
    if not folder.is_dir():
        raise FileNotFoundError(f"comparison not found: {cid}")
    candidates = []
    if prefer == "reference":
        candidates = ["reference-normalized.png", "reference.png", "actual-normalized.png", "actual.png"]
    else:
        candidates = ["actual-normalized.png", "actual.png", "reference-normalized.png", "reference.png"]
    for name in candidates:
        path = folder / name
        if path.is_file():
            return path
    raise FileNotFoundError(f"no PNG artifact in comparison {cid}")


def _read_meta(directory: Path) -> Dict[str, Any]:
    path = directory / META_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_meta(directory: Path, meta: Dict[str, Any]) -> None:
    path = directory / META_FILE
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
