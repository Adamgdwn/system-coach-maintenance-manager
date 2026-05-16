# Roadmap

## Current Baseline

The application currently provides local stack review, selected-root filesystem mapping, share summaries, read-only maintenance diagnostics, approval-required plan previews, a Request Desk, browser fallback mode, and local Ollama-backed coaching.

## Chunk 1: Governance And Release Hygiene

Status: completed.

- Keep governance level `1` and autonomy level `A1`.
- Keep execution disabled for generated maintenance and request plans.
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

Status: planned.

- Expand request families beyond cursor/pointer size:
  - display scaling, brightness, night light, and refresh rate
  - audio input/output selection and volume issues
  - network/DNS troubleshooting
  - package/update repair planning
  - Docker/container cleanup planning
  - startup app review
  - slow-computer guided triage
- Route unknown requests into a clarifying triage flow.
- Add request-plan tests for each supported family.
- Keep all generated plans approval-required and non-executing.

## Chunk 4: Maintenance History And Evidence

Status: planned.

- Add a local history/archive module for diagnostic snapshots, request plans, approval decisions, and future action results.
- Store records under a clear local-only directory such as `history/` or user-selected app data.
- Add a history view in GTK and browser mode.
- Add “known-good lessons” only when evidence supports them.
- Keep history exportable for support handoff.

## Chunk 5: Coach And UX Separation

Status: planned.

- Separate the combined coach page into clearer surfaces:
  - Chat
  - Request Desk
  - Approval Queue
  - History
- Make approval-required plans scannable with risk, reversibility, privilege, and exact commands.
- Add better empty states and “what changed since last run” summaries.
- Keep browser mode as the cross-platform baseline for Windows and Linux distributions.

## Chunk 6: Packaging And Sharing

Status: planned.

- Add setup guides for Ubuntu/Debian, Fedora, Arch, and Windows browser mode.
- Document Ollama setup and supported model tags.
- Add launcher/install guidance per platform.
- Decide whether to introduce packaging metadata such as `pyproject.toml`.
- Add release checklist coverage for Linux native mode and browser fallback mode.

## Chunk 7: Approved Action Runner Contract

Status: future, gated.

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

Status: future, governance reassessment required.

- Add a narrow action runner for reversible or low-risk maintenance tasks only after Chunk 7 is complete.
- Require per-action confirmation and visible logs.
- Start with user-space actions before any privileged actions.
- Reassess risk, autonomy, documentation, and approval controls before enabling privileged operations.
- Do not introduce autonomous execution until the tool has a long safety record.
