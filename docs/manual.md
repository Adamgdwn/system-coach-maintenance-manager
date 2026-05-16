# Manual

## Purpose

System Stack Review and Coach is a local-first desktop tool for understanding the machine it runs on. It explains installed development tools, maps user-selected filesystem roots, and offers local AI coaching through Ollama when available.

The next product direction is to grow this into a system maintenance and troubleshooting coach while keeping user approval at the center of any machine-changing action.

## Operating Model

- Local review probes run bounded, read-only checks.
- Filesystem mapping only scans roots selected by the user.
- AI coaching is grounded in the generated report and selected map.
- Maintenance diagnostics should begin as read-only observations and recommendations.
- Any future repair or cleanup action must require explicit user approval before execution.

## Governance

This project is set to governance level `1` with agent autonomy `A1`.

In practical terms, the tool may inspect, summarize, and recommend. It may prepare changes or commands, but machine-changing actions require user approval before they are applied.

## Common Workflows

1. Launch the desktop app with `bash launchers/run-stack-coach.sh`.
2. Run a local review to inspect the current environment and installed tools.
3. Optionally scan selected roots to discover projects and configuration files.
4. Ask the local coach questions about the detected stack or selected roots.
5. Use the Request Desk for specific approval-required plans, such as changing cursor size.
6. Copy a share summary when a plain-language environment overview is needed.

## Maintenance Direction

The maintenance-manager expansion should prioritize:

- read-only system health diagnostics
- clear severity and evidence for each finding
- guided troubleshooting flows for common symptoms
- command previews before any fix is run
- auditable logs of checks, recommendations, and approved actions
- Windows and Linux browser-mode support, with native Linux GTK mode where GTK is installed
