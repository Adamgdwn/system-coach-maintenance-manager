# Pop!_OS + COSMIC Agent

## Purpose

The Pop!_OS + COSMIC Agent is an intrinsic maintenance domain inside System Coach and Maintenance Manager. It is meant for Pop!_OS/COSMIC desktop, display, session, update, package-health, firmware-visibility, and UI symptoms.

The operating loop is:

1. Scan local evidence.
2. Identify likely surfaces and anomalies.
3. Assess risk, confidence, and privilege requirements.
4. Analyze with the local model ladder.
5. Learn from local history and Pop/COSMIC lessons.
6. Improve the recommended path.
7. Fix only the exact approved step.
8. Verify with fresh evidence and save a lesson.

## Modes

- Observe Mode: scan, research records, analysis, and suggestions only.
- Guided Fix Mode: low-risk guarded actions after exact confirmation.
- Full Control Mode: future higher-risk/elevated actions after explicit confirmation. This does not mean silent or unrestricted execution.

The current implementation is the MVP guided-fix slice. It can collect evidence, build ranked action recommendations, execute guarded low-risk Pop/COSMIC actions, verify, and save lessons. Package repair, firmware scheduling/install, release upgrade, OS refresh, package purge, broad autoremove, broad config deletion, and guessed service restarts remain blocked.

## Local Evidence

The scan collects bounded evidence from available commands such as:

- `/etc/os-release`
- `pgrep -a cosmic`
- `systemctl --user --failed --no-legend --plain`
- `journalctl --user -b --no-pager -n 500`
- `cosmic-randr list`
- `xrandr --query`
- `lspci -nnk`
- `lsusb`
- `apt-get check`
- `apt list --upgradable`
- `apt-mark showhold`
- `apt-cache policy ...`
- `flatpak remote-ls --updates`
- `fwupdmgr get-updates`

Scan output is capped and redacted for user paths, hostnames, and obvious tokens.

## Research

Web research is disabled by default. The initial research layer records trusted official sources without fetching remote page text unless research is explicitly enabled by project controls and the current request opts in. Safe research queries are built from the user symptom and sanitized profile facts, not raw logs.

The local API treats `project-control.yaml` as the source of truth for live Pop/COSMIC web research. Browser or API payloads cannot turn live research on when `pop_cosmic_agent.web_research_enabled` is `false`. Research responses include the effective mode, governance reason, and whether records are local/manual notes, official-source metadata, live web search, or live web fetch records.

Highest-trust sources are official System76 docs, System76 blog/release notes, and official Pop/COSMIC GitHub sources. Live fetches are HTTPS-only and restricted to official System76 hosts plus path-aware `pop-os` GitHub repository URLs. Community sources may be useful later, but should not justify risky fixes by themselves.

## Local Models

The Pop/COSMIC brain uses the existing local Ollama model ladder. The model can recommend only whitelisted `action_key` values. Deterministic code maps those keys to exact commands and action contracts.

The model may not invent executable shell commands or bypass the guarded catalog.

## Current Action Catalog

Executable low-risk/current-user actions:

- Run standard Pop/COSMIC evidence collection.
- Collect display evidence.
- Collect update/package evidence.
- Collect firmware visibility.
- Open COSMIC Settings.
- Open COSMIC Store.

Blocked escalation paths:

- Package repair.
- Firmware schedule/install.
- Release upgrade.
- OS refresh.
- Package purge/autoremove purge.
- Broad config deletion.
- Guessed service restarts.

Blocked recommendations are shown as human-readable escalation paths with next steps for collecting evidence and designing a new guarded contract. They are not presented as executable plans until the catalog and tests explicitly support them.

## Verification And Lessons

After execution, the agent can run a verification scan and save a local lesson under the Pop/COSMIC lesson cache. Lessons record the action result, action commands, post-scan evidence, and whether the user confirmed improvement. A completed command is stored as `completed_unconfirmed` until the user explicitly confirms the symptom improved. Lessons are retrieval records, not model fine-tuning.
