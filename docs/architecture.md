# Architecture Overview

## Summary

System Stack Review and Coach is a local-only educational and maintenance-coaching application that helps users understand the tools installed on their machine and inspect basic system health. It runs as a native GTK desktop application by default, executes local probe agents to inspect the environment, optionally maps user-approved filesystem roots, runs read-only maintenance diagnostics, and renders the results in a desktop shell. It can also use a local Ollama-served model to answer interactive questions about the detected environment and diagnostics. A browser-hosted mode remains available as a fallback.

## Components

- `src/stack_review_coach/desktop_app.py`: Native GTK desktop shell and primary local Linux user interface.
- `src/stack_review_coach/server.py`: Optional local HTTP server for browser fallback mode across Windows and Linux distributions.
- `src/stack_review_coach/agents.py`: Defines local probe agents that execute version and capability checks for system tools.
- `src/stack_review_coach/ai_engine.py`: Connects to the local Ollama service and builds coaching prompts from the report and filesystem map.
- `src/stack_review_coach/diagnostics.py`: Collects read-only maintenance facts such as disk, memory, load, services, logs, network basics, and package-manager health.
- `src/stack_review_coach/maintenance_reporting.py`: Turns maintenance diagnostics into ranked findings and approval-required plan previews.
- `src/stack_review_coach/request_plans.py`: Converts specific user requests into platform-aware approval-required plans without execution.
- `src/stack_review_coach/knowledge.py`: Contains built-in explanations for common development tools and stack pairings.
- `src/stack_review_coach/scanner.py`: Performs opt-in filesystem mapping for user-selected roots and discovers projects and config files.
- `src/stack_review_coach/reporting.py`: Converts raw probe results into learner-friendly summaries, recommendations, and stack pattern matches.
- `src/stack_review_coach/web/`: Browser UI assets for the interactive learning experience.
- `launchers/`: Shell scripts for local execution and desktop installation.

## Data Flow

1. The user launches the application through the CLI script or desktop launcher.
2. The native GTK shell opens and requests local review data.
3. Probe agents execute local commands on the same machine and collect outputs such as versions, paths, and environment metadata.
4. If the user opts in, the filesystem mapper scans only the selected locations.
5. The reporting layer enriches those findings with explanatory knowledge and compatibility notes.
6. If the user runs maintenance diagnostics, read-only checks collect system-health evidence and convert it into findings and approval-required plan previews.
7. If the user asks a question, the desktop shell builds a local prompt from the report, optional map, and optional maintenance diagnostics, then submits it to the local Ollama model.
8. The desktop shell renders the final report and AI coaching conversation for exploration and sharing.

The desktop shell adapts its layout based on window size so smaller screens can stack major panels vertically while larger screens stay side-by-side.

In browser fallback mode, the local HTTP server exposes equivalent report, maintenance, request-plan, and Ask The Coach endpoints.

No remote services are required, and no probe or filesystem results are transmitted off-machine by the application.

## Dependencies

- Python 3.12+
- Standard library modules only for runtime behavior
- GTK 3 via `python3-gi` for native Linux desktop mode
- A local Ollama service when interactive AI coaching is enabled
- Local operating-system commands when present, such as `python3`, `git`, `node`, or `docker`
- Optional read-only maintenance commands when present, such as Linux `findmnt`, `systemctl`, `journalctl`, `ip`, package-manager health checks, or Windows `wevtutil`, `route`, and `winget`
- Read access for any folders the user chooses to map

## Key Decisions

- ADR 0001 selects a local web GUI because `tkinter` was not available in the target Python environment.
- Agent controls were reassessed to `A1` because the tool now uses bounded local probe agents to execute read-only inspection commands.
- Filesystem mapping is opt-in and scope-based to avoid surprising broad scans across the machine.
- Local AI coaching uses an on-device model through Ollama so stack questions can stay within the local environment.
- Maintenance diagnostics are read-only in the current governance level. Prepared plans require approval and execution is disabled until the action runner is explicitly designed and reassessed.
- Browser mode is the portability baseline. Native Windows UI support is a future enhancement unless a cross-platform GUI toolkit is introduced.
