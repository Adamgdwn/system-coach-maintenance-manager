# Maintenance Manager Plan

## Product Posture

System Stack Review and Coach should grow into a local maintenance and troubleshooting coach before it becomes a fixer. The first maintenance versions should inspect, explain, prioritize, and prepare user-approved action plans.

The operating rule is:

- read-only diagnostics may run without extra approval
- filesystem scans remain opt-in and scope-bound
- generated repair plans must show exact commands and expected effects
- any machine-changing action requires explicit user approval
- privileged actions are separated from normal diagnostics

## Governance Boundary

Project governance is level `1` and agent autonomy is `A1`.

For this project, that means the tool may propose changes and prepare approved work, but it should not silently mutate the host machine. This is especially important as the product expands from development-stack explanation into system maintenance.

## What To Borrow From Chuwi Optimizer

Chuwi Optimizer is more autonomous than this project should be right now, but its architecture has useful patterns:

- **Doctor check**: a readiness pass that verifies dependencies, launchers, permissions, and environment assumptions before deeper work.
- **Metrics snapshot**: collect structured before/after machine state rather than relying on vague text output.
- **Experiment registry**: define possible maintenance actions as explicit records with ids, descriptions, privilege needs, and reversibility.
- **Dry-run default**: preview action impact before applying anything.
- **Evidence archive**: store run summaries, metrics, plans, and reflections so the user can audit what happened.
- **Reversibility metadata**: for actions that move files, keep manifests and restore commands.
- **Privileged boundary**: keep privileged scripts separate and require an explicit operator path.
- **Durable lessons gate**: only promote a lesson or known-good action when evidence shows it helped.
- **Interrupt/control file**: useful later for any long-running maintenance workflow.

The pieces not to copy yet:

- autonomous apply loops
- YOLO task mode
- privileged cleanup as a default path
- device-specific assumptions tied to Chuwi/Xubuntu/USB mode

## Proposed Architecture

Add a maintenance domain beside the existing stack-review domain:

- `diagnostics.py`: read-only system checks and evidence collection
- `maintenance_reporting.py`: converts diagnostic records into severity, plain-language explanations, and next steps
- `maintenance_actions.py`: future registry of possible repair plans and guarded commands
- `maintenance_history.py`: future archive of approved plans and outcomes

The desktop app can then add a Maintenance tab without disrupting the existing Summary, Components, Find And Map, and Ask The Coach flows.

## Diagnostic Record Shape

Each diagnostic should return a structured record:

```text
id
title
status
severity
category
summary
evidence
recommended_next_steps
commands_run
requires_privilege
can_prepare_action
```

This keeps the UI, reporting, exports, and local AI context aligned.

## First Diagnostic Set

Start with read-only checks:

- disk usage for home, root, and selected mounts
- memory and swap pressure
- CPU load compared with CPU count
- failed systemd services when `systemctl` is available
- recent high-priority journal errors with strict line limits
- network and DNS basics
- package-manager health signals without installing or removing anything
- backup/security posture as informational checks only

## Troubleshooting Flows

The first guided flows should be symptom-based:

- My computer is slow
- Disk is getting full
- Network or DNS is broken
- An app or service will not start
- Development tools are acting weird
- Updates or packages are stuck

Each flow should show what was checked, what evidence was found, what is uncertain, and what the safest next step is.

## Approved Action Path

When repair support is introduced, use this progression:

1. show issue and evidence
2. show proposed command or file operation
3. show risk, reversibility, and expected result
4. ask for explicit approval
5. run the approved action only
6. record output and follow-up diagnostic result
7. show rollback or manual recovery notes

No silent `sudo`, no broad cleanup defaults, and no autonomous loop until governance is reassessed.
