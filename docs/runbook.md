# Runbook

## Purpose

This system teaches users about their local development environment through a native desktop window. In normal operation it starts the GTK application, runs bounded local probe agents, and displays explanations for detected tools.

It can also perform an opt-in filesystem map for user-selected roots to explain project folders, repositories, and configuration files in plain language.
The maintenance diagnostics workflow runs read-only system health checks and prepares approval-required plans without executing fixes.
Maintenance reports and Request Desk plans are appended to a local JSONL history archive.
Prepared plans include approved-action contracts. Eligible current-user plans can execute after the user presses Execute. Eligible elevated plans can then ask for the operating-system administrator password/UAC approval before running.
When Ollama is available locally, it can answer follow-up questions using the local model and the generated stack, filesystem, and maintenance context.

## Alerts And Failures

Likely failure conditions:

- Python is unavailable or below the required version.
- The desktop window does not open or crashes at startup.
- GTK is unavailable on a non-Linux machine or a Linux distribution without `python3-gi`.
- A probe command hangs or is missing.
- A filesystem map root is too large, slow, or permission-limited.
- A maintenance diagnostic command is missing, times out, or returns permission-limited evidence.
- The local history archive cannot be written or read.
- An action contract appears blocked even though the user expects it to run.
- An elevated action does not show a password/UAC prompt or fails because `pkexec`, Polkit, PowerShell, or UAC is unavailable.
- Pop!_OS/COSMIC scan, analysis, research records, action planning, execution, verification, or lesson storage fails.
- Ollama is unavailable, has no supported model, or returns an error while answering.
- The desktop launcher points to an outdated repository path.

First response:

1. Run `bash launchers/run-system-coach.sh`.
2. If the desktop shell still fails, try `PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser` as a fallback.
3. On Windows, use `$env:PYTHONPATH="src"; python -m system_coach_maintenance_manager --browser`.
4. Check the command log in the UI to see which probe failed or timed out.
5. Refresh the local AI status line and confirm `ollama list` shows an installed model.
6. Reduce filesystem scan scope to one or two specific roots if mapping is slow.
7. Run maintenance diagnostics and review findings before preparing any machine-changing action.
8. Refresh the History view to confirm diagnostics and request plans are being recorded.
9. Check the Approval Queue to confirm each prepared plan shows exact commands and a clear execution state.
10. For Pop!_OS/COSMIC issues, run the dedicated deep scan, inspect the generated research records, ask the local model ladder, and build only one fix plan at a time.
11. If an action-run attempt is tested, confirm eligible user-level plans run only after the confirmation phrase, elevated plans show the OS authorization prompt, and ineligible plans record blocked reasons.

## Dependencies

- `python3`
- GTK 3 via `python3-gi`
- `ollama` with a supported local model for AI coaching
- The files under `src/system_coach_maintenance_manager/web/`
- Optional local tools being probed, such as `git`, `node`, `docker`, and `gh`
- Optional read-only maintenance commands such as `findmnt`, `systemctl`, `journalctl`, `ip`, and a local package manager
- Linux `pkexec`/Polkit for elevated execution
- Windows PowerShell and UAC for elevated execution
- Windows browser mode can use read-only commands such as `wevtutil`, `route`, and `winget` when present
- Read access for any folders the user chooses to map
- Write access to `history/maintenance-history.jsonl` or the directory configured by `SYSTEM_COACH_HISTORY_DIR`

## Recovery

- Commit and push normal repository updates directly to `main`. Use another branch only when the project owner explicitly asks for it.
- If the desktop shell does not load, retry from a terminal to surface runtime errors and use browser fallback mode if needed.
- If desktop launching fails, rerun `bash launchers/install-desktop-entry.sh`.
- If a specific tool is reported incorrectly, run its version command directly in a shell and compare the output.
- If filesystem mapping feels too broad, clear the selected roots and rerun with only the directories you want to inspect.
- If maintenance findings look noisy, inspect the command log and rerun after narrowing the symptom being investigated.
- If an approval-required plan is generated, review the exact command, target, risk, and rollback before pressing Execute. User-level and elevated plans can execute when the matching contract allows them.
- If a user request plan is generated, confirm the platform, command, target setting, reversibility, and approval gate before pressing Execute.
- If Request Desk appears to choose the wrong lane, read the Current Recommendation's hypothesis, evidence check, and alternate families; after execution, the app records a local learning note so later requests can improve.
- If the Pop!_OS + COSMIC Agent suggests package repair, firmware install, release upgrade, OS refresh, broad config deletion, or package purge, treat that as blocked escalation unless a future exact high-risk plan implements it.
- If Pop/COSMIC research is needed, enable web research deliberately and use sanitized symptoms/profile facts only. Do not paste full journal logs or private file contents into search queries.
- If an elevated action fails on Linux, confirm `pkexec` is installed and a Polkit authentication agent is running in the desktop session.
- If an elevated action fails on Windows, confirm PowerShell can launch UAC prompts for the current account.
- If an action contract says execution is blocked, review the gate reasons; placeholder, unsupported, uncatalogued, or insufficiently specified plans should remain blocked.
- If history does not update, check directory permissions or set `SYSTEM_COACH_HISTORY_DIR` to a writable local path.
- If the Approval Queue looks empty after a plan is prepared, refresh diagnostics or prepare the request again and check the browser console or terminal for errors.
- If AI answers fail, verify `ollama` is running locally and the model list includes a supported model such as `gemma4:latest`.
- If the window feels cramped, resize it; the shell should reflow between side-by-side and stacked layouts automatically.

## Escalation

Escalate to the project owner or technical lead when:

- the local launcher repeatedly fails on multiple machines
- a probe command causes unexpected side effects
- a maintenance diagnostic suggests a privileged, irreversible, broad cleanup, or high-risk system action outside the elevated catalog
- any user wants action execution enabled rather than preview-only contracts
- governance requirements or exception handling need review
