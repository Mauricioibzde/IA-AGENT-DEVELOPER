"""Heuristic patch planning/application for the correction loop (Phase 5)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from local_agent.checkpoint import RunCheckpoint
from local_agent.security import resolve_in_workspace


def plan_heuristic_patches(report: Dict[str, Any], *, max_patches: int = 8) -> List[Dict[str, Any]]:
    """Derive safe CSS-oriented patches from a visual report.

    These are best-effort nudges (layout/style), not full redesigns.
    """
    patches: List[Dict[str, Any]] = []
    layout_changes = report.get("layoutChanges") or report.get("layout_changes") or []
    if isinstance(report.get("layoutDiff"), dict):
        layout_changes = layout_changes or report["layoutDiff"].get("layoutChanges") or []

    for change in layout_changes:
        if len(patches) >= max_patches:
            break
        if not isinstance(change, dict):
            continue
        sel = str(change.get("selector") or "").strip()
        delta = change.get("delta") if isinstance(change.get("delta"), dict) else {}
        if not sel or not _safe_selector(sel):
            continue
        dw = int(delta.get("width") or 0)
        dh = int(delta.get("height") or 0)
        dx = int(delta.get("x") or 0)
        dy = int(delta.get("y") or 0)
        decls: List[str] = []
        # Invert delta: if actual is wider (+dw), shrink toward reference.
        if abs(dw) >= 2:
            decls.append(f"width: calc(100% + {-dw}px)" if abs(dw) < 80 else f"max-width: calc(100% + {-dw}px)")
        if abs(dh) >= 2 and abs(dh) < 120:
            decls.append(f"min-height: calc(1px + {-dh}px)" if dh < 0 else f"max-height: calc(100% + {-dh}px)")
        if abs(dx) >= 2 and abs(dx) < 80:
            decls.append(f"margin-left: {-dx}px")
        if abs(dy) >= 2 and abs(dy) < 80:
            decls.append(f"margin-top: {-dy}px")
        if not decls:
            continue
        patches.append(
            {
                "kind": "css_rule",
                "selector": sel,
                "declarations": decls,
                "reason": f"layout delta w={dw} h={dh} x={dx} y={dy}",
            }
        )

    for region in report.get("regions") or []:
        if len(patches) >= max_patches:
            break
        if not isinstance(region, dict):
            continue
        el = region.get("probableElement") or region.get("probable_element") or {}
        if not isinstance(el, dict):
            continue
        if el.get("confidence") not in {"high", "medium"}:
            continue
        sel = str(el.get("selector") or "").strip()
        if not sel or not _safe_selector(sel):
            continue
        if any(p.get("selector") == sel for p in patches):
            continue
        category = str(region.get("category") or "layout")
        decls = []
        if category in {"spacing", "layout"}:
            decls.append("box-sizing: border-box")
            decls.append("max-width: 100%")
        elif category == "typography":
            decls.append("line-height: 1.35")
        else:
            decls.append("box-sizing: border-box")
        patches.append(
            {
                "kind": "css_rule",
                "selector": sel,
                "declarations": decls,
                "reason": f"region {region.get('id')} ({category})",
            }
        )

    # Always ensure a visible correction trail file exists when we have any signal.
    if not patches and (report.get("similarity") or 0) < 0.999:
        patches.append(
            {
                "kind": "css_rule",
                "selector": ":root",
                "declarations": ["--forge-correction-pass: 1"],
                "reason": "marker pass for correction loop trail",
            }
        )
    return patches[:max_patches]


def _safe_selector(sel: str) -> bool:
    if len(sel) > 180:
        return False
    # Block obvious CSS injection / unbalanced constructs.
    if re.search(r"[{}@]|</|javascript:", sel, re.I):
        return False
    return bool(re.match(r"^[a-zA-Z0-9\s\.\#\:\-\_\[\]=\"\'>~+,*]+$", sel))


def apply_patches(
    workspace: Path,
    patches: List[Dict[str, Any]],
    *,
    run_id: str,
    relative_css: str = "correction-overrides.css",
) -> Dict[str, Any]:
    """Apply patches under checkpoint protection. Returns apply summary."""
    workspace = Path(workspace).resolve()
    checkpoint = RunCheckpoint(workspace, run_id)
    css_rel = relative_css.replace("\\", "/").lstrip("./")
    css_path = resolve_in_workspace(workspace, css_rel)
    checkpoint.snapshot_before(css_rel)

    existing = ""
    if css_path.is_file():
        try:
            existing = css_path.read_text(encoding="utf-8")
        except OSError:
            existing = ""

    blocks: List[str] = []
    for patch in patches:
        if patch.get("kind") != "css_rule":
            continue
        sel = patch.get("selector")
        decls = patch.get("declarations") or []
        if not sel or not decls:
            continue
        body = ";\n  ".join(str(d).rstrip(";") for d in decls)
        reason = str(patch.get("reason") or "").replace("*/", "* /")
        blocks.append(f"/* forge-correction: {reason} */\n{sel} {{\n  {body};\n}}\n")

    if not blocks:
        return {"ok": True, "written": [], "patches": 0, "checkpoint_id": run_id}

    css_path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n/* --- correction loop --- */\n\n"
    new_css = existing.rstrip() + (separator if existing.strip() else "") + "\n".join(blocks)
    css_path.write_text(new_css + "\n", encoding="utf-8")

    # Ensure index.html links the override stylesheet.
    index_rel = "index.html"
    index_path = workspace / index_rel
    linked = False
    if index_path.is_file():
        checkpoint.snapshot_before(index_rel)
        html = index_path.read_text(encoding="utf-8", errors="ignore")
        href = css_rel
        if href not in html:
            tag = f'<link rel="stylesheet" href="{href}" />'
            if "</head>" in html:
                html = html.replace("</head>", f"  {tag}\n</head>", 1)
            else:
                html = tag + "\n" + html
            index_path.write_text(html, encoding="utf-8")
            linked = True

    return {
        "ok": True,
        "written": [css_rel] + ([index_rel] if linked else []),
        "patches": len(blocks),
        "checkpoint_id": run_id,
        "linked_index": linked,
    }


def rollback_patches(workspace: Path, run_id: str) -> Dict[str, Any]:
    cp = RunCheckpoint.load(workspace, run_id)
    if not cp:
        return {"ok": False, "error": "checkpoint not found", "run_id": run_id}
    return cp.restore()
