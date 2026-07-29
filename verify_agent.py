#!/usr/bin/env python3
"""Manual verification helper for a short agent workflow."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import ollama_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify agent write + validate flow")
    parser.add_argument("--model", default=ollama_agent.DEFAULT_MODEL)
    parser.add_argument("--workspace", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace or tempfile.mkdtemp(prefix="ia-agent-verify-")
    Path(workspace).mkdir(parents=True, exist_ok=True)

    prompt = (
        'Create a source file called src/app.js with the content console.log("hello"); '
        "and then validate that the file exists"
    )
    print(f"workspace={workspace}")
    print(
        ollama_agent.run_agent(
            prompt,
            workspace=workspace,
            model=args.model,
            max_steps=4,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
