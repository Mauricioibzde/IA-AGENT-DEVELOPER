"""Report / request models for the Visual Engine (Phase 1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

SideType = Literal["url", "image", "artifact"]


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
        data.pop("raw", None)
        data["raw"] = self.raw
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
