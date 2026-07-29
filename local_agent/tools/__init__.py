"""Tool package exports."""

from __future__ import annotations

from ..tool_registry import ToolRegistry, register_many
from .filesystem import build_filesystem_tools
from .git_tools import build_git_tools
from .patch_tools import build_patch_tools
from .project_tools import build_project_tools
from .search import build_search_tools
from .terminal import build_terminal_tools


def build_default_registry(*, include_git: bool = True) -> ToolRegistry:
    registry = ToolRegistry()
    register_many(registry, build_filesystem_tools())
    register_many(registry, build_terminal_tools())
    register_many(registry, build_patch_tools())
    register_many(registry, build_search_tools())
    register_many(registry, build_project_tools())
    if include_git:
        register_many(registry, build_git_tools())
    return registry
