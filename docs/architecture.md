# Architecture Overview

## Summary

System Coach and Maintenance Manager is a local-only educational and maintenance-coaching application that helps users understand the tools installed on their machine and inspect basic system health. It runs as a native GTK desktop application by default, executes local probe agents to inspect the environment, optionally maps user-approved filesystem roots, runs read-only maintenance diagnostics, and renders the results in separated review, Request Desk, Approval Queue, History, and Chat surfaces. It can also use a local Ollama-served model to answer interactive questions about the detected environment and diagnostics. A browser-hosted mode remains available as a fallback.

## Components

- `src/system_coach_maintenance_manager/desktop_app.py`: Native GTK desktop shell and primary local Linux user interface.
- `src/system_coach_maintenance_manager/server.py`: Optional local HTTP server for browser fallback mode across Windows and Linux distributions.
- `src/system_coach_maintenance_manager/agents.py`: Defines local probe agents that execute version and capability checks for system tools.
- `src/system_coach_maintenance_manager/ai_engine.py`: Connects to the local Ollama service, selects Gemma 4 when available, builds coaching prompts, and provides structured Request Desk reasoning.
- `src/system_coach_maintenance_manager/diagnostics.py`: Collects read-only maintenance facts such as disk, memory, load, services, logs, network basics, and package-manager health.
- `src/system_coach_maintenance_manager/followup_plans.py`: Turns completed evidence actions or plain display-layout intent into the next exact guarded request when the evidence is strong enough.
- `src/system_coach_maintenance_manager/maintenance_actions.py`: Defines approved-action contracts, guarded eligibility checks, and completed, failed, or blocked action-result records.
- `src/system_coach_maintenance_manager/maintenance_history.py`: Appends local JSONL history records for diagnostic snapshots, request plans, approval decisions, action results, and learning notes.
- `src/system_coach_maintenance_manager/maintenance_reporting.py`: Turns maintenance diagnostics into ranked findings and approval-required plan previews.
- `src/system_coach_maintenance_manager/pop_cosmic_profile.py`: Detects Pop!_OS release, COSMIC session signals, System76 indicators, GPU basics, secure boot visibility, and available support commands without sudo.
- `src/system_coach_maintenance_manager/pop_cosmic_deep_scan.py`: Collects bounded, redacted Pop!_OS/COSMIC evidence across profile, services, logs, display, GPU, updates, config inventory, and suspend/wake scopes.
- `src/system_coach_maintenance_manager/pop_cosmic_research.py`: Builds source-aware Pop/COSMIC research records from official sources and optional enabled providers without sending raw local logs.
- `src/system_coach_maintenance_manager/pop_cosmic_knowledge.py`: Stores local Pop/COSMIC research records, action records, and lessons in JSONL caches.
- `src/system_coach_maintenance_manager/pop_cosmic_brain.py`: Uses the local Ollama model ladder to analyze Pop/COSMIC scans, research records, and lessons into hypotheses and whitelisted action keys.
- `src/system_coach_maintenance_manager/pop_cosmic_actions.py`: Maps Pop/COSMIC action keys to exact guarded action contracts or blocked escalation plans.
- `src/system_coach_maintenance_manager/request_evidence.py`: Collects bounded read-only facts relevant to a Request Desk symptom before Gemma reasons over it.
- `src/system_coach_maintenance_manager/request_plans.py`: Converts specific user requests into platform-aware approval-required plans, including deeper display/dock evidence plans for external-monitor and pointer-behavior symptoms.
- `src/system_coach_maintenance_manager/knowledge.py`: Contains built-in explanations for common development tools and stack pairings.
- `src/system_coach_maintenance_manager/scanner.py`: Performs opt-in filesystem mapping for user-selected roots and discovers projects and config files.
- `src/system_coach_maintenance_manager/reporting.py`: Converts raw probe results into learner-friendly summaries, recommendations, and stack pattern matches.
- `src/system_coach_maintenance_manager/troubleshooting_model.py`: Defines the universal troubleshooting method and system-access assumptions used by Gemma prompts.
- `src/system_coach_maintenance_manager/web/`: Browser UI assets for the interactive learning experience.
- `launchers/`: Shell scripts for local execution and desktop installation.
- `pyproject.toml`: Packaging metadata and console entry point.

## Data Flow

1. The user launches the application through the CLI script or desktop launcher.
2. The native GTK shell opens and requests local review data.
3. Probe agents execute local commands on the same machine and collect outputs such as versions, paths, and environment metadata.
4. If the user opts in, the filesystem mapper scans only the selected locations.
5. The reporting layer enriches those findings with explanatory knowledge and compatibility notes.
6. If the user runs maintenance diagnostics, read-only checks collect system-health evidence and convert it into findings and approval-required plan previews.
7. Request Desk collects bounded read-only evidence relevant to the accumulated request, such as display topology, audio devices, routes, package-manager state, Docker usage, startup entries, performance basics, services, or logs.
8. Request Desk sends the accumulated user request, operating-system hint, desktop hint, recent maintenance findings, request evidence, and recent local learning notes to the local Gemma model for structured hypothesis building and clarification.
9. The deterministic planner accepts only whitelisted model-selected investigation lanes, then prepares the concrete approval-required plan. Display/dock symptoms are routed to topology and compositor evidence collection before any fix is proposed.
10. Prepared plans receive an approved-action contract; eligible current-user plans can run when the user presses Execute, and eligible elevated plans can request administrator/root authorization through the operating system prompt.
11. The Pop!_OS + COSMIC Agent can run its own scan, prepare source-aware research records, ask the local model ladder for hypotheses and ranked whitelisted action keys, build an exact guarded plan, execute after confirmation, verify with a fresh scan, and save a local lesson.
12. After a guarded action completes, the local model reviews the captured output and summarizes findings, likely cause, and the best next fix direction.
13. If the completed action was an evidence plan and the output names an exact safe fix, or if a plain COSMIC display-layout request can be resolved from local evidence, the follow-up planner prepares the next approval-required executable recommendation in Request Desk.
14. Maintenance reports, Request Desk plans, completed, failed, or blocked action results, and short action-result learning notes can be appended to local history for later review and future Request Desk context.
15. If the user asks a question, the desktop shell builds a local prompt from the report, optional map, and optional maintenance diagnostics, then submits it to the local Ollama model.
16. The desktop shell renders the final report, approval queue, history, and AI coaching conversation for exploration and sharing.

The desktop shell adapts its layout based on window size so smaller screens can stack major panels vertically while larger screens stay side-by-side.

In browser fallback mode, the local HTTP server exposes equivalent report, maintenance, request-plan, history, and Ask The Coach endpoints.

No remote services are required, and no probe or filesystem results are transmitted off-machine by the application.

## Dependencies

- Python 3.12+
- Standard library modules only for runtime behavior
- GTK 3 via `python3-gi` for native Linux desktop mode
- A local Ollama service when interactive AI coaching is enabled
- Local operating-system commands when present, such as `python3`, `git`, `node`, or `docker`
- Optional read-only maintenance commands when present, such as Linux `findmnt`, `systemctl`, `journalctl`, `ip`, package-manager health checks, or Windows `wevtutil`, `route`, and `winget`
- Linux `pkexec`/Polkit or Windows PowerShell/UAC for elevated execution
- Read access for any folders the user chooses to map
- Write access to the local history directory, `history/` by default or `SYSTEM_COACH_HISTORY_DIR` when configured

## Key Decisions

- ADR 0001 selects a local web GUI because `tkinter` was not available in the target Python environment.
- Agent controls were reassessed to `A1` because the tool now uses bounded local probe agents to execute read-only inspection commands.
- The Request Desk uses a universal troubleshooting method rather than issue-specific diagnosis prompts: restate the symptom, form hypotheses, gather local evidence, compare against known-good state, choose the smallest useful action, verify, and record the lesson.
- System-access prompts tell Gemma it may reason from everything the local app can view and may prepare plans at any privilege/risk level, while deterministic governance decides whether a plan can execute as current user, request OS administrator/root authorization, or remain blocked/manual.
- Filesystem mapping is opt-in and scope-based to avoid surprising broad scans across the machine.
- Local AI coaching uses an on-device model through Ollama so stack questions can stay within the local environment.
- Maintenance diagnostics remain read-only by default. Gemma is allowed to build and reassess hypotheses, but command selection and execution eligibility remain deterministic. Prepared plans require approval, and eligible guarded plans execute only when the user presses Execute.
- The Pop!_OS + COSMIC Agent is a domain-specific guided-fix flow. Its model layer recommends action keys only; deterministic code maps those keys to exact commands. Risky package, firmware, release-upgrade, refresh, purge, broad config, and guessed restart paths remain blocked until implemented as narrow high-risk flows.
- Approved-action contracts make execution requirements visible, including whether a plan runs as the current user or through an elevated OS authorization prompt.
- Local history is JSONL so support handoff can use regular file tools without a database dependency.
- Browser mode is the portability baseline. Native Windows UI support is a future enhancement unless a cross-platform GUI toolkit is introduced.
