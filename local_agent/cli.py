"""Command-line interface for the local coding agent."""

from __future__ import annotations

import argparse
import sys

from .agent import CodingAgent
from .config import AgentConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Ollama coding agent")
    parser.add_argument("prompt", help="Task to perform")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--model", default=None, help="Default/coder Ollama model")
    parser.add_argument("--planner-model", default=None, help="Planner model")
    parser.add_argument("--reflection-model", default=None, help="Reflection model")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum global steps")
    parser.add_argument("--max-task-attempts", type=int, default=None, help="Attempts per task")
    parser.add_argument("--command-timeout", type=int, default=None, help="Command timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="Do not mutate files or run commands")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--debug", action="store_true", help="Debug JSON logs")
    parser.add_argument("--plan-only", action="store_true", help="Create plan without executing")
    parser.add_argument("--no-memory", action="store_true", help="Disable long-term memory")
    parser.add_argument("--no-git", action="store_true", help="Disable git tools")
    parser.add_argument(
        "--auto-approve-low-risk",
        action="store_true",
        default=True,
        help="Auto-approve low/medium risk mutating tools (default)",
    )
    parser.add_argument("--config", default=None, help="Optional JSON/.env config file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AgentConfig.from_args(
        args.workspace,
        model=args.model,
        planner_model=args.planner_model,
        reflection_model=args.reflection_model,
        max_steps=args.max_steps,
        max_task_attempts=args.max_task_attempts,
        command_timeout=args.command_timeout,
        dry_run=args.dry_run,
        verbose=args.verbose,
        debug=args.debug,
        plan_only=args.plan_only,
        no_memory=args.no_memory,
        no_git=args.no_git,
        auto_approve_low_risk=args.auto_approve_low_risk,
        config_path=args.config,
    )
    report = CodingAgent(config).run(args.prompt)
    print(report.render())
    if report.status.value in {"FAILED", "BLOCKED"}:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
