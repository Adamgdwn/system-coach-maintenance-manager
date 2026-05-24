# Windows Browser Mode Setup Guide

Native GTK mode is Linux-first. On Windows, use browser mode as the supported baseline.

## Requirements

- Python 3.12+
- Git for Windows
- Optional Ollama for local AI coaching
- A modern browser

## Run From PowerShell

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m system_coach_maintenance_manager --browser
```

To start without opening a browser automatically:

```powershell
$env:PYTHONPATH = "src"
python -m system_coach_maintenance_manager --browser --no-browser
```

The server binds to `127.0.0.1` by default and prints the local URL.

## Optional Ollama Setup

Install Ollama for Windows, then pull the preferred local model:

```powershell
ollama pull qwen3:8b
ollama pull gemma4:latest
ollama list
```

The app will fall back to another installed local model if the preferred tag is unavailable.

## Optional Bring-Your-Own-Key Cloud Setup

Set your API key in PowerShell before launching browser mode. The app stores only the environment variable name, not the key value:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:PYTHONPATH = "src"
python -m system_coach_maintenance_manager --browser
```

Open Model Provider Setup, choose bring-your-own-key cloud mode, and use `OPENAI_API_KEY` as the key environment variable. Executable commands are still selected by deterministic guarded planners, not by the cloud model.

## Local History

Maintenance diagnostics and Request Desk plans are written to `history\maintenance-history.jsonl` by default. To move the archive:

```powershell
$env:SYSTEM_COACH_HISTORY_DIR = "$env:LOCALAPPDATA\SystemCoachMaintenanceManager\history"
```

## Supported Workflows

- Local review and command log
- Browser Request Desk
- Approval Queue
- Maintenance History
- Coach Chat through local Ollama when available
- Read-only Windows maintenance probes when tools such as `wevtutil`, `route`, and `winget` are available

## Validation

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
python -m system_coach_maintenance_manager --browser --no-browser
```
