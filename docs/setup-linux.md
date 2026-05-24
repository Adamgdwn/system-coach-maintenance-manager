# Linux Setup Guide

## Ubuntu And Debian

Install system dependencies:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0 git
```

Optional AI coaching:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b
ollama pull gemma4:latest
```

Optional bring-your-own-key cloud setup stores only an environment-variable name in the app config. Put the key in your shell environment instead:

```bash
export OPENAI_API_KEY="your-key-here"
PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser
```

Then open Model Provider Setup and select bring-your-own-key cloud mode. Command execution remains deterministic and approval-gated.

Run from the repository:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager
```

Optional editable install with the console command:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
system-coach
```

Install the desktop launcher:

```bash
bash launchers/install-desktop-entry.sh
```

Browser fallback:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser
```

## Fedora

Install system dependencies:

```bash
sudo dnf install python3 python3-gobject gtk3 git
```

Run:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager
```

## Arch Linux

Install system dependencies:

```bash
sudo pacman -S python python-gobject gtk3 git
```

Run:

```bash
PYTHONPATH=src python -m system_coach_maintenance_manager
```

## Local History

Maintenance diagnostics and Request Desk plans are written to `history/maintenance-history.jsonl` by default. To move the archive:

```bash
export SYSTEM_COACH_HISTORY_DIR="$HOME/.local/share/system-coach-maintenance-manager/history"
```

## Validation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall src tests
bash scripts/governance-preflight.sh
```
