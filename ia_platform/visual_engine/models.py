"""Report / request models for the Visual Engine (Phase 1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

SideType = Literal["url", "image", "artifact"]

# Bridge fields needed by UI + heuristic correction patches.
_PROMOTE_FROM_RAW = (
    "layoutChanges",
    "regions",
    "domChanges",
    "layoutDiff",
    "styleChanges",
    "normalization",
    "domDiff",
    "metrics",
    "comparisonId",
)


@dataclass
class Side:
    type: SideType
    value: str


@dataclass
class CompareRequest:
    source: Side
    target: Side
    viewport: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    comparison_id: Optional[str] = None


@dataclass
class VisualReport:
    comparison_id: str
    status: str
    mode: str
    similarity: Optional[float]
    viewport: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        raw = dict(self.raw or {})
        data.pop("raw", None)
        # Promote bridge payload fields so correction/UI do not need to dig into raw.
        for key in _PROMOTE_FROM_RAW:
            if key in raw and (key not in data or data.get(key) in (None, {}, [])):
                data[key] = raw[key]
        if raw.get("comparisonId"):
            data["comparisonId"] = raw["comparisonId"]
        elif data.get("comparison_id") and "comparisonId" not in data:
            data["comparisonId"] = data["comparison_id"]
        # Prefer richer artifacts from bridge when present.
        if isinstance(raw.get("artifacts"), dict) and raw["artifacts"]:
            data["artifacts"] = raw["artifacts"]
        data["raw"] = raw
        return data

    @classmethod
    def from_bridge(cls, payload: Dict[str, Any]) -> "VisualReport":
        return cls(
            comparison_id=str(payload.get("comparisonId") or payload.get("comparison_id") or ""),
            status=str(payload.get("status") or "unknown"),
            mode=str(payload.get("mode") or "unknown"),
            similarity=payload.get("similarity"),
            viewport=dict(payload.get("viewport") or {}),
            artifacts=dict(payload.get("artifacts") or {}),
            summary=dict(payload.get("summary") or {}),
            warnings=list(payload.get("warnings") or []),
            recommendations=list(payload.get("recommendations") or []),
            raw=payload,
        )
