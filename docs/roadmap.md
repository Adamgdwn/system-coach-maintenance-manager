# Roadmap

## Current Baseline

The application currently provides local stack review, selected-root filesystem mapping, share summaries, read-only maintenance diagnostics, separated Chat, Gemma-backed Request Desk reasoning, Approval Queue, local maintenance history, guarded current-user and elevated action execution, a universal troubleshooting mental model, evidence-backed follow-up planning, plain-language COSMIC display layout fixes, a Pop!_OS + COSMIC guided agent MVP, browser fallback mode, local Ollama-backed coaching, and platform setup/release guidance.

## Chunk 1: Governance And Release Hygiene

Status: completed.

- Initially keep governance level `1` and autonomy level `A1`.
- Initially keep execution disabled for generated maintenance and request plans.
- Snapshot the current supervised maintenance milestone in version control.
- Update the risk register for maintenance diagnostics, request planning, Windows/browser support, and approval-plan risks.
- Remove stale governance-path references from exception/risk docs.
- Clean duplicate wording in architecture and user-facing docs.

## Chunk 2: Platform-Specific Plan Hardening

Status: completed.

- Split maintenance plan generation by platform instead of reusing Linux commands for every operating system.
- Add Windows-native plan text for event logs, route/DNS inspection, package-manager review, and settings requests.
- Add Linux desktop-environment detection hints for GNOME, KDE, Xfce, COSMIC, and unknown sessions.
- Add tests that mock Linux and Windows diagnostics separately.
- Ensure unsupported platforms return explicit triage plans rather than weak command guesses.

## Chunk 3: Request Desk Expansion

Status: completed.

- Expand request families beyond cursor/pointer size:
  - display scaling, brightness, night light, and refresh rate
  - display/dock investigation for rotated external monitors, hidden screen regions, and pointer jitter
  - audio input/output selection and volume issues
  - network/DNS troubleshooting
  - package/update repair planning
  - Docker/container cleanup planning
  - startup app review
  - slow-computer guided triage
- Route unknown requests into a clarifying triage flow.
- Add request-plan tests for each supported family.
- Keep all generated plans approval-required; execution support is introduced later through guarded user-level and elevated action chunks.

## Chunk 4: Maintenance History And Evidence

Status: completed.

- Add a local history/archive module for diagnostic snapshots, request plans, approval decisions, and future action results.
- Store records under a clear local-only directory such as `history/` or user-selected app data.
- Add a history view in GTK and browser mode.
- Add “known-good lessons” only when evidence supports them.
- Keep history exportable for support handoff.

## Chunk 5: Coach And UX Separation

Status: completed.

- Separate the combined coach page into clearer surfaces:
  - Chat
  - Request Desk
  - Approval Queue
  - History
- Make approval-required plans scannable with risk, reversibility, privilege, and exact commands.
- Add better empty states and “what changed since last run” summaries.
- Keep browser mode as the cross-platform baseline for Windows and Linux distributions.

## Chunk 6: Packaging And Sharing

Status: completed.

- Add setup guides for Ubuntu/Debian, Fedora, Arch, and Windows browser mode.
- Document Ollama setup and supported model tags.
- Add launcher/install guidance per platform.
- Decide whether to introduce packaging metadata such as `pyproject.toml`.
- Add release checklist coverage for Linux native mode and browser fallback mode.

## Chunk 7: Approved Action Runner Contract

Status: completed.

- Define the action-runner contract before implementation:
  - exact command preview
  - expected effect
  - privilege requirement
  - reversibility
  - timeout
  - output capture
  - post-check
  - rollback notes
- Require explicit per-action confirmation.
- Record approved actions and outputs in history.
- Keep privileged actions separated from normal diagnostics.

## Chunk 8: Guarded Maintenance Actions

Status: completed.

- Add a narrow action runner for reversible or low-risk maintenance tasks only after Chunk 7 is complete.
- Require per-action confirmation and visible logs.
- Start with user-space actions before any privileged actions.
- Reassess risk, autonomy, documentation, and approval controls before enabling privileged operations.
- Do not introduce autonomous execution until the tool has a long safety record.

## Chunk 9: Guarded Execution Enablement

Status: completed.

- Keep project controls at governance level `1` and autonomy level `A1`, with `action_runner_enabled: true` for user-approved guarded execution.
- Make the desktop Execute button run enabled low-risk user-level plans instead of only showing blocked review text.
- Keep this chunk limited to exact, reversible, non-privileged commands in the guarded catalog.
- Keep privileged, destructive, placeholder, medium-risk, and unsupported plans blocked with visible reasons until the later elevated execution chunk.
- Record completed, failed, and blocked action attempts in local history.

## Chunk 10: Interactive Request Desk

Status: completed.

- Add a Send button and Enter-to-send behavior for request intake.
- Keep a visible request conversation instead of jumping straight from a text field to a plan.
- Ask plain follow-up questions when the request is too vague.
- Prepare the guarded plan from the accumulated conversation once enough detail is present.

## Chunk 11: Gemma Reasoning Brain

Status: completed.

- Route Request Desk intake through local Gemma 4 when Ollama is available.
- Collect bounded read-only request evidence before Gemma asks the user for details.
- Ask Gemma for structured JSON containing request family, readiness, clarification questions, and reasoning summary.
- Accept only whitelisted request families from the model before preparing a deterministic guarded plan.
- Keep command selection, execution eligibility, approval controls, and guarded catalog enforcement outside the model.
- Analyze completed guarded action output with Gemma so Execute produces useful findings and next-fix direction.
- Simplify the desktop Request Desk and Approval Queue so the default view is a plain-language current recommendation and selected-fix card.
- Add Request Desk in-place execution so the user does not have to switch tabs to run the current guarded recommendation.

## Chunk 12: Elevated System Execution

Status: completed.

- Add an explicit elevated execution mode for plans that require administrator/root privileges.
- Enable elevated plans through `elevated_action_runner_enabled: true` in project controls.
- Use Linux `pkexec`/Polkit to show a password prompt for elevated actions.
- Use Windows PowerShell/UAC as the Windows elevated execution path.
- Keep elevated execution approval-required, exact-command-only, catalog-gated, and recorded in history.
- Show execution mode and elevation prompt details in the desktop recommendation and review surfaces.
- Keep unsupported, placeholder, and uncatalogued elevated plans blocked with visible reasons.

## Chunk 13: Pop!_OS + COSMIC Guided Agent MVP

Status: completed.

- Add a dedicated Pop!_OS + COSMIC agent surface in desktop and browser mode.
- Detect Pop!_OS, COSMIC session signals, System76 hardware hints, GPU state, secure boot visibility, and local support commands.
- Add bounded read-only deep scans for standard, display, updates, and full evidence scopes.
- Redact home paths, hostnames, obvious secrets, and cap collected output before model analysis or history storage.
- Add local research records, lesson memory, action records, and verification scans for Pop/COSMIC troubleshooting.
- Use the local model ladder for Pop/COSMIC analysis while keeping command selection deterministic and catalog-gated.
- Register Qwen 3, Gemma 4 latest, DeepSeek, GPT-OSS, and Qwen-VL local model roles.
- Add guarded low-risk Pop/COSMIC actions for evidence collection and opening COSMIC Settings or COSMIC Store.
- Keep package repair, firmware schedule/install, release upgrade, OS refresh, package purge, broad autoremove, broad config deletion, guessed service restarts, and display-layout mutation blocked in this agent slice.
- Document the operating loop: scan, identify, assess, analyze, learn, improve, fix approved steps, verify, and save lessons.

## Chunk 14: Server-Side Action Contract Integrity And Local API Safety

Status: completed.

- Stop treating client-submitted action contracts as authoritative for execution.
- Store or rebuild executable contracts server-side from known plan/action identifiers.
- Require confirmation phrases to match the server-held contract, not a contract echoed back by the client.
- Reject forged `execution_enabled`, forged confirmation phrases, changed command previews, and mismatched plan/action ids.
- Preserve the existing command allowlist as a second execution gate after contract integrity checks.
- Add API and unit tests proving forged normal, elevated, and Pop/COSMIC contracts cannot run.
- Record blocked forgery attempts in local history with clear reasons.

## Chunk 15: Pop/COSMIC Research Governance Enforcement

Status: completed.

- Make `/api/pop-cosmic/research` obey `project-control.yaml` instead of request-body overrides.
- Keep live web research disabled unless project controls explicitly enable it.
- Distinguish local-only research records, official-source metadata records, and live fetched web records in the response and history.
- Ensure raw local logs are never sent to research providers; only sanitized symptom/profile queries may leave the machine.
- Add tests proving browser/API payloads cannot override disabled web research.
- Add a visible governance reason when research is local-only because live research is disabled.

## Chunk 16: Source Allowlist And Research Scope Tightening

Status: completed.

- Replace broad host-only GitHub allowance with path-aware Pop/COSMIC repository rules.
- Keep official System76 docs, System76 blog/release notes, and official Pop/COSMIC GitHub sources in separate trust tiers.
- Reject non-HTTPS, unknown-domain, and unrelated GitHub URLs before any fetch.
- Add tests for allowed System76 URLs, allowed Pop/COSMIC GitHub URLs, rejected broad GitHub URLs, and rejected unrelated domains.
- Keep community sources advisory only; they may inform questions or evidence requests, but not justify risky fixes by themselves.

## Chunk 17: Pop/COSMIC Agent Robustness Polish

Status: completed.

- Add server/API tests for Pop/COSMIC profile, deep scan, research, analyze, plan, execute, and verify endpoints.
- Improve verification lessons so they record the action result, observed post-scan evidence, and whether improvement was user-confirmed.
- Add a blocked-escalation output path that prepares human-readable next steps without presenting blocked actions as executable.
- Improve browser and desktop error states for missing COSMIC commands, unavailable Ollama, timed-out scans, and disabled web research.
- Re-run governance, unit tests, compile checks, and a live Pop/COSMIC smoke test before promoting the next agent milestone.

## Chunk 18: Portable System Discovery For Public Users

Status: completed.

- Make first-run onboarding assume an unknown machine, not Adam's Pop!_OS workstation.
- Detect operating system, distribution, desktop environment, package managers, hardware class, GPU, display stack, available privilege helpers, installed local model runtimes, and available maintenance commands.
- Build a local capability profile that decides which agent surfaces are shown, which scans are available, which actions are blocked, and which docs are most relevant.
- Keep Pop!_OS + COSMIC as a first-class specialization while allowing Ubuntu/Debian, Fedora, Arch, Windows browser mode, GNOME, KDE, Xfce, and unknown desktops to degrade gracefully.
- Store machine-specific preferences and learned lessons locally, never in the repository.
- Add tests with mocked system profiles so public-user customization does not regress Pop/COSMIC behavior.

## Chunk 19: Model Provider And Bring-Your-Own-Key Setup

Status: completed.

- Default to local models through Ollama or another explicitly configured local runtime when available.
- Do not ship bundled API keys, shared tokens, or owner-funded cloud credentials.
- Add a provider setup screen that clearly separates:
  - local model mode with no external API key
  - bring-your-own-key cloud mode
  - no-model deterministic fallback mode
- Store provider settings in a local user config file or environment variables, with secrets excluded from history, logs, reports, and Git.
- Add provider health checks that explain what is available and what is missing without failing the rest of the app.
- Keep command selection and execution gates deterministic even when a cloud model is configured.
- Document recommended local models and optional cloud-provider setup in README and setup guides.

## Chunk 20: Public GitHub Release Readiness

Status: completed.

- Update README for public users with a clear "what this can and cannot do" section.
- Explain that users need either a local model/runtime, a bring-your-own provider key, or acceptance of deterministic no-model fallback behavior.
- Add installation and first-run instructions for Linux and browser fallback mode.
- Add privacy documentation describing what is collected locally, what may be sent to model providers, and how to disable web/cloud features.
- Add a public safety model covering approval-required actions, elevated execution, blocked destructive actions, research controls, and local history.
- Add sample screenshots or text walkthroughs for first-run discovery, Request Desk, Approval Queue, and Pop/COSMIC Agent.
- Add release checklist items for public distribution, secret scanning, dependency review, and fresh-clone smoke tests.
