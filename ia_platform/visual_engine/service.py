"""High-level Visual Engine API used by Forge routes / agent (Phase 1–2)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from local_agent.security import resolve_in_workspace

from .bridge import VisualEngineBridgeError, node_available, ping, run_cli
from .history import append_history, delete_comparison, get_history_entry, load_history
from .models import CompareRequest, Side, VisualReport
from .security import validate_compare_url
from . import telemetry


class VisualEngine:
    def __init__(
        self,
        project_dir: Path,
        *,
        allowed_loopback_ports: Optional[Set[int]] = None,
        forge_port: int = 8787,
        project_id: str = "",
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.project_id = project_id or self.project_dir.name
        self.artifacts_root = self.project_dir / ".agent" / "visual"
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        ports = set(allowed_loopback_ports or set())
        ports.add(forge_port)
        ports.update(range(9200, 9300))
        self.allowed_loopback_ports = ports
        self.forge_port = forge_port

    def available(self) -> bool:
        return node_available()

    def status(self) -> Dict[str, Any]:
        from .cleanup import cleanup_stats

        info: Dict[str, Any] = {
            "ok": self.available(),
            "node": self.available(),
            "artifacts_root": str(self.artifacts_root),
            "project_id": self.project_id,
            "telemetry": telemetry.snapshot(),
            "storage": cleanup_stats(self.artifacts_root),
        }
        if self.available():
            try:
                info["bridge"] = ping()
            except VisualEngineBridgeError as exc:
                info["ok"] = False
                info["error"] = str(exc)
        else:
            info["error"] = "Node.js 18+ required (cd visual_engine && npm install)"
        return info

    def list_comparisons(self) -> List[Dict[str, Any]]:
        return load_history(self.artifacts_root)

    def get_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        return get_history_entry(self.artifacts_root, comparison_id)

    def delete_comparison(self, comparison_id: str) -> bool:
        return delete_comparison(self.artifacts_root, comparison_id)

    def resolve_preview_url(
        self,
        *,
        host_header: str = "127.0.0.1:8787",
        mode: str = "auto",
        file_path: str = "index.html",
    ) -> str:
        """Build a capture URL for this project's preview (static Forge or live dev)."""
        from ia_platform.dev_server import dev_manager

        rel = (file_path or "index.html").lstrip("/")
        status = dev_manager.status(self.project_id, self.project_dir)
        if mode in {"dev", "auto"} and status.get("running") and status.get("url"):
            url = str(status["url"]).rstrip("/") + "/"
            return url
        host = (host_header or f"127.0.0.1:{self.forge_port}").split(",")[0].strip()
        if "://" in host:
            base = host.rstrip("/")
        else:
            base = f"http://{host}"
        return f"{base}/preview/{self.project_id}/{rel}"

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

    def _record(self, report: VisualReport, *, source: Dict[str, Any], target: Dict[str, Any]) -> VisualReport:
        entry = {
            "comparisonId": report.comparison_id,
            "status": report.status,
            "mode": report.mode,
            "similarity": report.similarity,
            "viewport": report.viewport,
            "summary": report.summary,
            "artifacts": report.artifacts,
            "warnings": report.warnings,
            "source": source,
            "target": target,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "projectId": self.project_id,
        }
        append_history(self.artifacts_root, entry)
        return report

    def compare_images(self, source_rel: str, target_rel: str, **options: Any) -> VisualReport:
        req = CompareRequest(
            source=Side(type="image", value=source_rel),
            target=Side(type="image", value=target_rel),
            options=options or {"inline": True},
        )
        return self.compare(req)

    def compare(self, request: CompareRequest) -> VisualReport:
        if not self.available():
            raise VisualEngineBridgeError("Visual Engine requires Node.js 18+")
        source = self._resolve_side(request.source)
        target = self._resolve_side(request.target)
        options = dict(request.options or {})
        inline = bool(options.pop("inline", False)) and source["type"] == "image" and target["type"] == "image"
        t0 = time.time()
        ok = True
        try:
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
            report = VisualReport.from_bridge(data)
            if not inline:
                self._record(report, source=source, target=target)
            return report
        except Exception:
            ok = False
            raise
        finally:
            telemetry.record("compare", duration_ms=(time.time() - t0) * 1000, ok=ok)
            try:
                telemetry.persist(self.artifacts_root)
            except OSError:
                pass

    def compare_multi(
        self,
        *,
        source: Side,
        target: Side,
        viewports: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[VisualReport]:
        """One CLI process, one browser pool, many viewports."""
        if not self.available():
            raise VisualEngineBridgeError("Visual Engine requires Node.js 18+")
        src = self._resolve_side(source)
        tgt = self._resolve_side(target)
        opts = dict(options or {})
        t0 = time.time()
        ok = True
        try:
            data = run_cli(
                {
                    "op": "compare_multi",
                    "source": src,
                    "target": tgt,
                    "viewports": viewports,
                    "options": opts,
                    "artifactsRoot": str(self.artifacts_root),
                },
                timeout=int(opts.get("timeoutMs") or 600),
            )
            reports = []
            for raw in data.get("reports") or []:
                report = VisualReport.from_bridge(raw)
                self._record(report, source=src, target=tgt)
                reports.append(report)
            return reports
        except Exception:
            ok = False
            raise
        finally:
            telemetry.record("compare_multi", duration_ms=(time.time() - t0) * 1000, ok=ok)
            try:
                telemetry.persist(self.artifacts_root)
            except OSError:
                pass

    def capture_url(self, url: str, *, viewport: Optional[Dict[str, Any]] = None, **options: Any) -> VisualReport:
        validate_compare_url(url, allowed_loopback_ports=self.allowed_loopback_ports)
        t0 = time.time()
        ok = True
        try:
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
            report = VisualReport.from_bridge(data)
            self._record(
                report,
                source={"type": "url", "value": url},
                target={"type": "capture", "value": url},
            )
            return report
        except Exception:
            ok = False
            raise
        finally:
            telemetry.record("capture", duration_ms=(time.time() - t0) * 1000, ok=ok)

    def capture_preview(
        self,
        *,
        host_header: str = "127.0.0.1:8787",
        mode: str = "auto",
        file_path: str = "index.html",
        viewport: Optional[Dict[str, Any]] = None,
        **options: Any,
    ) -> VisualReport:
        url = self.resolve_preview_url(host_header=host_header, mode=mode, file_path=file_path)
        return self.capture_url(url, viewport=viewport, **options)
