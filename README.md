# IA Agent Developer

Local Ollama-based coding agent for file creation, project scaffolding, and simple validation.

## What it does
- Creates and edits files inside a sandboxed workspace
- Scaffolds starter projects (`node`, `python`, `react`)
- Validates that files or folders exist
- Uses Ollama as the reasoning engine (`/api/chat`, with `/api/generate` fallback)

## Project structure
- `ollama_agent.py` — main agent + tools
- `ollama-create-file.ps1` — optional PowerShell helper
- `verify_agent.py` — manual end-to-end check
- `tests/` — unit tests (no Ollama required for most cases)

## Requirements
- Python 3.10+
- [Ollama](https://ollama.com/) installed locally
- A model available, for example `qwen3-coder:30b`

## Quick start

```bash
# optional: install test tooling
python -m pip install -e ".[dev]"

# start Ollama in another terminal
ollama serve

# pull a model if needed
ollama pull qwen3-coder:30b

# run the agent
python ollama_agent.py "Create a file called demo.txt with the content hello"
```

Useful flags:

```bash
python ollama_agent.py --dry-run "Create a starter project called app_demo"
python ollama_agent.py --verbose "List files in the current folder"
python ollama_agent.py --model qwen3-coder:30b --workspace ./sandbox "Criar pasta tmp"
```

Environment variables:
- `OLLAMA_HOST` — default `http://127.0.0.1:11434`
- `OLLAMA_MODEL` — default `qwen3-coder:30b`

## Example commands

Create a Node starter project:

```bash
python ollama_agent.py "Create a starter project called app_demo in folder app_demo"
```

Create a Python starter:

```bash
python ollama_agent.py "Create a python starter project called demo_py in folder demo_py"
```

Validate a folder:

```bash
python ollama_agent.py "Validate the files in the app_demo folder"
```

## Tests

```bash
python -m pytest -q
```

Live Ollama smoke test is skipped automatically when the daemon is offline.

## Safety notes
- Tool paths are resolved inside `--workspace` and cannot escape it
- `run_command` prefers argv execution when a shell is not required
- `replace_in_file` fails if the old text is missing
- Prefer `--dry-run` when exploring risky prompts

## Notes
This project is intentionally isolated from AzubiForge so it can evolve as a standalone agent prototype.
