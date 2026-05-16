# Risk Register

## Current Risk Classification

- Tier: medium
- Owner: Adam Goodwin
- Last reviewed: 2026-05-16

## Key Risks

| ID | Risk | Likelihood | Impact | Controls | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Governance checks can drift if local controls and repository standards diverge. | Low | Medium | `scripts/governance-preflight.sh` now runs the repository-local `automation/governance_check.sh`; `project-control.yaml` documents governance level `1` and agent autonomy `A1`; preflight is required before substantial changes. | Adam Goodwin | Mitigated |
| R-002 | Probe agents may misidentify or miss tools in unusual local environments. | Medium | Medium | Short command timeouts, visible command log, bounded read-only probes, manual verification path in runbook. | codex session | Open |
| R-003 | Desktop launcher can become stale if the repository is moved after installation. | Medium | Low | Reinstall script, documented recovery steps, launcher path kept explicit. | Adam Goodwin | Open |
| R-004 | Filesystem mapping could scan a broader area than a user intended. | Medium | Medium | Opt-in root selection, no automatic full-system crawl, local-only processing, visible selected roots in UI. | codex session | Open |
| R-005 | Local AI coaching may produce incomplete or slightly incorrect explanations. | Medium | Medium | Local model status visibility, prompt grounded in the actual report/map, friendly but bounded coaching style, user can inspect raw findings directly. | codex session | Open |
| R-006 | Maintenance diagnostics may overstate or understate noisy operating-system evidence. | Medium | Medium | Diagnostics are read-only, command outputs are visible, findings preserve evidence, and recommendations require manual review before action. | codex session | Open |
| R-007 | Request or maintenance plans could produce commands that do not match the host platform. | Medium | Medium | Plan generation branches by platform, unsupported platforms return triage plans without commands, and tests cover Linux and Windows command families. | codex session | Open |
| R-008 | Users may mistake approval-required previews for permission to execute changes. | Medium | High | Every plan marks `approval_required: true` and `execution_enabled: false`; UI status says no change was executed; future action runner work is gated behind roadmap chunks and governance reassessment. | codex session | Open |
| R-009 | Browser fallback support may lag native Linux behavior on Windows or less common Linux distributions. | Medium | Medium | Browser mode is treated as the cross-platform baseline, lazy imports avoid GTK requirements, and platform-specific request-plan hints are passed through the local API. | codex session | Open |
| R-010 | Future privileged or modifying maintenance actions could raise the project risk tier. | Medium | High | Action execution is disabled, guarded action-runner work is explicitly future-gated, and governance must be reassessed before privileged operations or higher autonomy. | Adam Goodwin | Open |
