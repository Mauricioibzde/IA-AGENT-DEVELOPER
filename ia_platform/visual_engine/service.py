"""High-level Visual Engine API used by Forge routes / agent (Phase 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set

from local_agent.security import resolve_in_workspace

from .bridge import VisualEngineBridgeError, node_available, run_cli
from .models import CompareRequest, Side, VisualReport
from .security import validate_compare_url


class VisualEngine:
    def __init__(
        self,
        project_dir: Path,
        *,
        allowed_loopback_ports: Optional[Set[int]] = None,
        forge_port: int = 8787,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.artifacts_root = self.project_dir / ".agent" / "visual"
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        ports = set(allowed_loopback_ports or set())
        ports.add(forge_port)
        ports.update(range(9200, 9300))
        self.allowed_loopback_ports = ports

    def available(self) -> bool:
        return node_available()

    def _resolve_side(self, side: Side) -> Dict[str, str]:
        if side.type == "url":
            validate_compare_url(side.value, allowed_loopback_ports=self.allowed_loopback_ports)
            return {"type": "url", "value": side.value}
        if side.type in {"image", "artifact"}:
            path = resolve_in_workspace(self.project_dir, side.value)
            if not path.is_file():
                raise FileNotFoundError(f"Image not found: {side.value}")
            return {"type": "image", "value": str(path)}
        raise ValueError(f"Unsupported side type: {side.type}")

    def compare_images(self, source_rel: str, target_rel: str, **options: Any) -> VisualReport:
        req = CompareRequest(
            source=Side(type="image", value=source_rel),
            target=Side(type="image", value=target_rel),
            options=options or {"inline": True},
        )
        # Prefer artifact-writing compare; tests may use inline via options.
        return self.compare(req)

    def compare(self, request: CompareRequest) -> VisualReport:
        if not self.available():
            raise VisualEngineBridgeError("Visual Engine requires Node.js 18+")
        source = self._resolve_side(request.source)
        target = self._resolve_side(request.target)
        options = dict(request.options or {})
        inline = bool(options.pop("inline", False)) and source["type"] == "image" and target["type"] == "image"

        payload: Dict[str, Any] = {
            "op": "compare_images" if inline else "compare",
            "source": source,
            "target": target,
            "viewport": request.viewport or {"width": 1366, "height": 768},
            "options": options,
            "artifactsRoot": str(self.artifacts_root),
            "comparisonId": request.comparison_id,
            "inline": inline,
        }
        data = run_cli(payload, timeout=int(options.get("timeoutMs") or 180))
        if inline and "similarity" in data and "artifacts" not in data:
            # Normalize inline metrics into a VisualReport-shaped object.
            data = {
                "comparisonId": request.comparison_id or "inline",
                "status": data.get("status") or "completed",
                "mode": data.get("mode") or "image-vs-image",
                "similarity": data.get("similarity"),
                "viewport": request.viewport or {},
                "summary": {
                    "differentPixels": data.get("diffPixels"),
                    "totalPixels": data.get("totalPixels"),
                    "diffPercent": data.get("diffPercent"),
                },
                "warnings": data.get("warnings") or [],
                "artifacts": {},
                **data,
            }
        return VisualReport.from_bridge(data)

    def capture_url(self, url: str, *, viewport: Optional[Dict[str, Any]] = None, **options: Any) -> VisualReport:
        validate_compare_url(url, allowed_loopback_ports=self.allowed_loopback_ports)
        data = run_cli(
            {
                "op": "capture",
                "url": url,
                "viewport": viewport or {"width": 1366, "height": 768},
                "options": options,
                "artifactsRoot": str(self.artifacts_root),
            },
            timeout=int(options.get("timeoutMs") or 120),
        )
        return VisualReport.from_bridge(data)
