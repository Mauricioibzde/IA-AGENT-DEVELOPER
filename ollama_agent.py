#!/usr/bin/env python3
"""Backward-compatible entrypoint for the modular local_agent package."""

from __future__ import annotations

import argparse
import os
import sys

from local_agent.agent import run_agent
from local_agent.config import AgentConfig
from local_agent.security import WorkspaceSecurityError, resolve_in_workspace
from local_agent.tool_registry import infer_tool_call_from_text, parse_tool_call, parse_tool_calls
from local_agent.tools import build_default_registry

# Re-exports used by legacy tests/scripts.
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def execute_tool(tool_name: str, args: dict, workspace: str, *, dry_run: bool = False, verbose: bool = False):
    config = AgentConfig.from_args(workspace, dry_run=dry_run, verbose=verbose, no_memory=True)
    registry = build_default_registry(include_git=True)
    # Normalize legacy aliases already registered.
    result = registry.execute(tool_name, args or {}, workspace=str(config.workspace), config=config)
    return result.to_dict()


def call_model(prompt: str, model: str = DEFAULT_MODEL, verbose: bool = False) -> str:
    from local_agent.ollama_client import OllamaClient
    from local_agent.logging_config import AgentLogger

    config = AgentConfig.from_args(".", model=model, verbose=verbose, no_memory=True)
    return OllamaClient(config, AgentLogger(config)).complete(prompt, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tool-using Ollama agent")
    parser.add_argument("prompt", help="Task to perform")
    parser.add_argument("--workspace", default=os.getcwd(), help="Workspace root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--max-steps", type=int, default=12, help="Maximum tool iterations")
    parser.add_argument("--dry-run", action="store_true", help="Plan tool actions without writing disk or running commands")
    parser.add_argument("--verbose", action="store_true", help="Print diagnostics")
    parser.add_argument("--plan-only", action="store_true", help="Only create a plan")
    args = parser.parse_args()
    print(
        run_agent(
            args.prompt,
            args.workspace,
            model=args.model,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            verbose=args.verbose,
            plan_only=args.plan_only,
        )
    )


if __name__ == "__main__":
    main()
