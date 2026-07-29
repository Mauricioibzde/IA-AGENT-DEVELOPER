# IA Agent Developer

This repository contains a local Ollama-based agent prototype for file creation, project scaffolding, and simple validation tasks.

## What it does
- Creates files inside the workspace
- Creates simple starter projects
- Validates that files or folders exist
- Uses Ollama as the reasoning engine through the local API

## Project structure
- `ollama_agent.py`: main agent implementation
- `ollama-create-file.ps1`: PowerShell helper for creating files via Ollama
- `verify_agent.py`: simple verification script
- `tests/`: basic test examples

## Requirements
- Ollama installed locally
- A model available, such as `qwen3-coder:30b`
- Python 3.10+

## Quick start
1. Start the Ollama service:
   ```powershell
   ollama serve
   ```
2. Run the agent from this folder:
   ```powershell
   & "c:/Users/Mauricio ibz/.local/bin/python3.14.exe" .\ollama_agent.py "Create a file called demo.txt with the content hello"
   ```

## Example commands
Create a starter project:
```powershell
& "c:/Users/Mauricio ibz/.local/bin/python3.14.exe" .\ollama_agent.py "Create a starter project called app_demo in a folder app_demo"
```

Validate files:
```powershell
& "c:/Users/Mauricio ibz/.local/bin/python3.14.exe" .\ollama_agent.py "Validate the files in the app_demo folder"
```

## Notes
This project is intentionally isolated from the AzubiForge application so it can evolve as a separate agent prototype and be shared independently.
