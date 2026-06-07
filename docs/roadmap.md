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

## Chunk 21: GitHub Public Alpha Handoff And Template

Status: completed.

- Update GitHub repository metadata so the public About panel accurately describes the project.
- Add accurate topics for platform, runtime, agent, maintenance, and local-first discovery.
- Switch from private-preview licensing to MIT so public users can download, use, fork, and contribute.
- Add sanitized README screenshots and release assets for the browser overview, capability profile, guarded request plans, model provider setup, and Pop/COSMIC agent.
- Publish the `v0.1.0-alpha` prerelease with alpha caveats, safety boundaries, validation notes, and screenshot assets.
- Add branch protection requiring the `validation` CI check while leaving owner emergency control available.
- Capture the whole GitHub public-alpha posture in `docs/github-public-alpha-handoff.md` so it can become a repeatable template for other repositories.

## Chunk 22: Autonomy And Depth Control Framework

Status: completed — 2026-06-07 09:33.

- Record owner governance decision: risk_tier lowered to low at G1; autonomy gate is the compensating control.
- Add `agent_autonomy_level` (A0–A4) and `agent_depth_level` (D1–D4) to `project-control.yaml`.
- Create `autonomy_controls.py`: loads both settings, exposes `can_auto_execute(tier)` and `max_depth()`.
- Update `maintenance_actions.py` and `action_plan_registry.py` execution gates to read autonomy level.
- Add `docs/adrs/0002-autonomy-depth-model.md` recording the tier definitions and compensating controls.
- Tests: autonomy gate blocks out-of-level execution, depth gate returns correct scope.
- Non-goals: no UI yet, no changes to existing guarded catalog.

## Chunk 23: Conversation Engine Core

Status: planned.

- Create `agent_conversation.py`: owns session state, conversation history, pending action tracking, and streaming token assembly.
- Public interface: `start_session()`, `submit_message(handle, text)`, `on_event(handle, callback)`.
- Events emitted: `agent_token`, `action_proposed`, `action_result`, `session_done`, `error`.
- Reads autonomy and depth level from `autonomy_controls.py` on session start.
- Does NOT own UI, diagnostic execution, or action execution — calls existing modules through their public APIs.
- Tests: state machine transitions, autonomy-level event suppression, concurrent-safe callback ordering.
- Non-goals: no GTK changes, no streaming to Ollama yet.

## Chunk 24: Parallel Diagnostics And Agent Probes

Status: planned.

- Wrap `collect_diagnostics()` checks in `concurrent.futures.ThreadPoolExecutor`; all eight checks run in parallel.
- Wrap `build_agents()` probe execution in the same pattern in `server.py` and `desktop_app.py`.
- Move `import json` from inside `_mount_snapshot()` to the top of `diagnostics.py`.
- Add 30-second TTL cache for `get_engine_status()` in `ai_engine.py`; expose `invalidate_engine_cache()`.
- Tests: parallel result set matches serial result set on mock data; cache returns stale value within TTL and fresh after.
- Non-goals: no streaming, no new diagnostic probes yet.

## Chunk 25: Auto-Launch Diagnostic Greeting

Status: planned.

- On desktop open, trigger diagnostics and agent probes automatically via `agent_conversation.py`.
- Conversation engine formats results as a natural opening message; streams tokens into the session.
- States: loading ("Checking your machine…"), healthy empty ("Everything looks clean — anything on your mind?"), findings present (brief summary + one open question), partial-failure ("I couldn't complete all checks — here's what I got").
- Greeting generator is a pure function in `agent_conversation.py` tested independently of GTK.
- Tests: greeting output for healthy, degraded, and empty diagnostic mocks; partial-failure state.
- Non-goals: no GTK bubble UI yet (greeting posts to a stub callback), no aesthetic changes.

## Chunk 26: Conversation Bubble UI

Status: planned.

- Replace desktop main area with a `Gtk.ListBox` conversation thread.
- Agent bubbles left-aligned; user bubbles right-aligned; command output in monospace inline blocks.
- Single `Gtk.Entry` input bar at the bottom; Enter submits, Shift-Enter inserts newline.
- Streaming: `agent_token` events append text to the active bubble via `GLib.idle_add`.
- Suggested reply chips (flat `Gtk.Button` row) appear below agent messages when options are provided.
- UX states: typing indicator while agent is working; disabled input while diagnostics run; scroll-to-bottom on new message.
- Non-goals: no aesthetic overhaul yet, Approval Queue tab kept until Chunk 27.

## Chunk 27: Inline Action Approval

Status: planned.

- Action proposals surface as inline cards in the conversation thread instead of the Approval Queue tab.
- Card shows: title, risk, reversible flag, privilege level, command preview, and action buttons.
- At A1: "Run it" requires explicit click. At A2: countdown timer (5 s, cancelable) then auto-fires. At A3+: fires immediately with a cancel window. At A0: card not shown; agent states it cannot act.
- Execution still goes through `action_plan_registry.execute_registered_action()`; server-side integrity gate unchanged.
- Result streams inline below the card; history record written as before.
- Remove Approval Queue tab and its panel code once inline cards are live.
- Tests: each autonomy level produces correct card behavior on mock action; duplicate-click prevention; countdown cancellation.
- Non-goals: no elevated Polkit UI changes.

## Chunk 28: Streaming AI Responses

Status: planned.

- Add streaming code path to `ai_engine.py` using Ollama `stream: true` NDJSON output.
- Conversational responses (greeting analysis, question answers, action result summaries) use streaming.
- JSON-structured reasoning calls (request family, maintenance plan) keep `stream: false`.
- `agent_conversation.py` emits `agent_token` events as tokens arrive; GTK bubble updates in real time.
- Graceful fallback: if streaming fails mid-response, emit what arrived and an error event.
- Tests: token sequence assembled correctly from mock NDJSON; fallback fires on truncated stream.
- Non-goals: no streaming for structured JSON calls, no Ollama API changes.

## Chunk 29: Aesthetic And UX Redesign

Status: planned.

- CSS-only overhaul: warm dark background, monospace throughout, terminal-style command blocks, conversation bubble styling, minimal chrome.
- Remove grid and panel visual elements from Review and History surfaces; surface their content inline in the conversation or as collapsible drawers.
- Thin persistent status strip at top: disk %, memory %, active model name, working pulse indicator.
- No behavior changes in this chunk — pure style and layout.
- Validate: all existing UX states (loading, empty, success, error) remain legible in new theme.
- Non-goals: no new features, no GTK widget changes.

## Chunk 30: Diagnostic Depth Expansion

Status: planned.

- Add D2 probes to `diagnostics.py`: CPU/GPU temperature via `sensors`, NVMe health via `nvme smart-log`, top memory/CPU consumers via `/proc`.
- Add D3 probes: `dmesg` error grouping, `lspci`/`lsusb` device enumeration, `journalctl -b` boot log summary, display topology via `cosmic-randr` or `wlr-randr`.
- Each probe gated by `autonomy_controls.max_depth()` — D1 behaviour unchanged at default settings.
- Agent conversation surfaces depth-specific findings with plain-language summaries.
- Tests: D2 and D3 probes return correct shape on mocked command output; D1 session does not call D2/D3 commands.
- Non-goals: no root-required probes, no firmware reads.

## Chunk 31: History Pruning And Private AI Boundary Cleanup

Status: planned.

- Add configurable `max_history_records` (default 500) to `maintenance_history.py`; prune oldest on write when exceeded.
- Expose `call_model(model, prompt, *, format_json, timeout)` as a public function in `ai_engine.py`; update `pop_cosmic_brain.py` to use it instead of importing `_post_json` and `_extract_json_object` directly.
- `request_plans.py` family routing split: extract each family's `_prepare_*_plan()` into a `plans/` subpackage; `request_plans.py` becomes a thin router over the subpackage's public API.
- Tests: history file prunes correctly at limit boundary; `pop_cosmic_brain` still produces valid analysis through the new public interface.
- Non-goals: no behavior changes to existing plan families, no new plan families.
