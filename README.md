# IA Agent Developer

This folder contains a local Ollama-based agent prototype for file creation, project scaffolding, and simple validation tasks.

## Files
- ollama_agent.py: main agent implementation
- ollama-create-file.ps1: PowerShell helper for creating files via Ollama
- verify_agent.py: simple verification script

## Usage
Run the agent from this folder:

```powershell
& "c:/Users/Mauricio ibz/.local/bin/python3.14.exe" .\ollama_agent.py "Create a file called demo.txt with the content hello"
```
