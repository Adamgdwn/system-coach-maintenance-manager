# Runbook

## Purpose

This system teaches users about their local development environment through a native desktop window. In normal operation it starts the GTK application, runs bounded local probe agents, and displays explanations for detected tools.

It can also perform an opt-in filesystem map for user-selected roots to explain project folders, repositories, and configuration files in plain language.
The maintenance diagnostics workflow runs read-only system health checks and prepares approval-required plans without executing fixes.
When Ollama is available locally, it can answer follow-up questions using the local model and the generated stack, filesystem, and maintenance context.

## Alerts And Failures

Likely failure conditions:

- Python is unavailable or below the required version.
- The desktop window does not open or crashes at startup.
- GTK is unavailable on a non-Linux machine or a Linux distribution without `python3-gi`.
- A probe command hangs or is missing.
- A filesystem map root is too large, slow, or permission-limited.
- A maintenance diagnostic command is missing, times out, or returns permission-limited evidence.
- Ollama is unavailable, has no supported model, or returns an error while answering.
- The desktop launcher points to an outdated repository path.

First response:

1. Run `bash launchers/run-stack-coach.sh`.
2. If the desktop shell still fails, try `PYTHONPATH=src python3 -m stack_review_coach --browser` as a fallback.
3. On Windows, use `$env:PYTHONPATH="src"; python -m stack_review_coach --browser`.
4. Check the command log in the UI to see which probe failed or timed out.
5. Refresh the local AI status line and confirm `ollama list` shows an installed model.
6. Reduce filesystem scan scope to one or two specific roots if mapping is slow.
7. Run maintenance diagnostics and review findings before preparing any machine-changing action.

## Dependencies

- `python3`
- GTK 3 via `python3-gi`
- `ollama` with a supported local model for AI coaching
- The files under `src/stack_review_coach/web/`
- Optional local tools being probed, such as `git`, `node`, `docker`, and `gh`
- Optional read-only maintenance commands such as `findmnt`, `systemctl`, `journalctl`, `ip`, and a local package manager
- Windows browser mode can use read-only commands such as `wevtutil`, `route`, and `winget` when present
- Read access for any folders the user chooses to map

## Recovery

- If the desktop shell does not load, retry from a terminal to surface runtime errors and use browser fallback mode if needed.
- If desktop launching fails, rerun `bash launchers/install-desktop-entry.sh`.
- If a specific tool is reported incorrectly, run its version command directly in a shell and compare the output.
- If filesystem mapping feels too broad, clear the selected roots and rerun with only the directories you want to inspect.
- If maintenance findings look noisy, inspect the command log and rerun after narrowing the symptom being investigated.
- If an approval-required plan is generated, treat it as a preview only. This version does not execute maintenance fixes.
- If a user request plan is generated, confirm the platform, command, target setting, reversibility, and approval gate before any future execution support is considered.
- If AI answers fail, verify `ollama` is running locally and the model list includes a supported model such as `gemma4:latest`.
- If the window feels cramped, resize it; the shell should reflow between side-by-side and stacked layouts automatically.

## Escalation

Escalate to the project owner or technical lead when:

- the local launcher repeatedly fails on multiple machines
- a probe command causes unexpected side effects
- a maintenance diagnostic suggests a privileged, irreversible, or broad cleanup action
- governance requirements or exception handling need review
