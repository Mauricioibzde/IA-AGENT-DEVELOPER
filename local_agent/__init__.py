"""Public package exports for the local coding agent."""

from __future__ import annotations

__version__ = "0.3.0"

from .agent import run_agent
from .config import AgentConfig

__all__ = ["AgentConfig", "run_agent", "__version__"]
