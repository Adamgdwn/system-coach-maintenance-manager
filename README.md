# System Coach and Maintenance Manager

## Purpose

System Coach and Maintenance Manager is a local-first desktop app that helps people understand and maintain the development environment already sitting in front of them. It inspects the current machine with small local probe agents, explains what installed tools do, highlights common stack patterns, runs read-only maintenance diagnostics, and presents the results in a guided native GUI built for new to intermediate coders and system owners.

The tool also supports opt-in filesystem mapping and interactive local AI coaching. Users choose which roots the app may inspect, and the app turns common project files and config locations into a readable map of what is on the machine, what each part generally does, and how the pieces fit together.

The maintenance workflow is intentionally supervised. The app can diagnose, explain, prepare approval-required plans, and execute eligible guarded plans only after the user presses Execute. Current-user plans run directly when they pass the contract; elevated plans use the operating system password/UAC prompt.

If you have ever asked "What is actually installed here?" or "Why do these tools seem to work together?", this app is meant to answer that in plain language without shipping your machine data anywhere else.

## Status

- Owner: Adam Goodwin
- Technical lead: codex session
- Risk tier: medium
- Production status: local desktop app ready to share and explore

## Quick Start

Requirements:

- Python 3.12+
- `python3-gi` for the native Linux GTK desktop shell
- `ollama` for interactive local AI coaching
- A graphical Linux desktop session for native mode, or any desktop with a browser for fallback mode
- `pkexec`/Polkit on Linux or PowerShell/UAC on Windows for elevated actions

Run locally in the native desktop shell:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager
```

Install in editable mode if you want the console entry point:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
system-coach
```

Use the launcher script:

```bash
bash launchers/run-system-coach.sh
```

Optional browser fallback:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser
```

On Windows, use browser mode first:

```powershell
$env:PYTHONPATH="src"; python -m system_coach_maintenance_manager --browser
```

Install the desktop entry:

```bash
bash launchers/install-desktop-entry.sh
```

Validate:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall src tests
```

## How It Works

- A native GTK desktop shell is the default user interface.
- Browser fallback mode is the cross-platform interface for Windows and Linux distributions without GTK.
- A portable capability profile assumes an unknown first-run machine, detects operating system, desktop, package managers, model runtimes, privilege helpers, and available maintenance commands, then decides which agent surfaces and docs fit that machine.
- Model Provider Setup defaults to local Ollama models, supports bring-your-own-key cloud readiness through environment variables, and keeps no-model deterministic fallback available.
- Probe agents run local commands such as `python3 --version`, `git --version`, and `docker compose version`.
- Users can opt into filesystem mapping for selected roots such as home directories, project folders, or `/etc`.
- Read-only maintenance diagnostics inspect system health signals such as disk pressure, memory, CPU load, failed services, recent critical logs, network basics, and package-manager health across Linux and Windows where platform tools are available.
- Maintenance plans are prepared as approval-required previews with commands, expected effects, risk, reversibility, and privilege flags.
- The Request Desk turns specific requests into platform-aware approval-required plans for cursor/pointer size, display settings, audio routing, network/DNS issues, package/update repair, Docker cleanup review, startup app review, and slow-computer triage.
- The Pop!_OS + COSMIC Agent adds a dedicated scan, concern, research-record, local-model analysis, fix-plan, execute, verify, and learn flow for COSMIC desktop issues.
- The Approval Queue makes prepared plans scannable before execution.
- Approved-action contracts are attached to prepared plans so command previews, confirmation phrases, timeouts, output capture policy, post-checks, and rollback notes are visible.
- Guarded action execution runs exact catalogued commands only after user approval. Elevated plans can request administrator/root approval through Linux `pkexec`/Polkit or Windows UAC.
- Model providers can help classify, explain, and reason about evidence, but deterministic planners and guarded action contracts still choose executable commands.
- Plain-language COSMIC display layout requests such as rotating the right monitor resolve against local display evidence and can produce executable `cosmic-randr` plans with rollback.
- Local maintenance history records diagnostic snapshots, request-plan previews, action results, and learning notes under `history/maintenance-history.jsonl` by default.
- History includes a “changed since last diagnostic run” summary when at least two diagnostic snapshots are available.
- Browser fallback mode includes both the Request Desk and local Coach Chat so Windows users can use the supervised workflow without GTK.
- The app can use a local Ollama model as its coaching engine to answer questions about the detected stack and mapped roots.
- The reporting layer turns raw findings into learner-friendly summaries, compatibility notes, and next-step coaching.
- The GUI can generate a shareable plain-language summary from local findings.
- The native desktop shell adapts between wider side-by-side and narrower stacked layouts as the window size changes.
- A browser-hosted interface remains available as an optional fallback mode.

## Why It’s Useful

- It helps newer developers connect installed tools to real workflows instead of memorizing names in isolation.
- It makes unfamiliar machines easier to understand before diving into a project.
- It gives teams a simple way to share a high-level local stack overview without writing a long manual first.
- It stays local-first, so users can choose what to inspect and what to keep private.
- It can answer follow-up questions about your machine using a local model instead of only static output.
- It can help users troubleshoot system health issues without silently changing the machine.

## Documentation

- `docs/architecture.md`
- `docs/deployment-guide.md`
- `docs/runbook.md`
- `docs/maintenance-manager-plan.md`
- `docs/system-capability-profile.md`
- `docs/model-provider-setup.md`
- `docs/pop-cosmic-agent.md`
- `docs/action-runner-contract.md`
- `docs/setup-linux.md`
- `docs/setup-windows-browser.md`
- `docs/release-checklist.md`
- `docs/CHANGELOG.md`
- `docs/risks/risk-register.md`
- `docs/adrs/0001-local-web-gui.md`
- `docs/exceptions/EX-2026-04-05-governance-home.md`

## Support Model

This project is maintained as a shareable local desktop tool. Operational issues should first be handled by checking Python and GTK availability, launcher behavior, and whether local probe commands succeed on the target machine.
