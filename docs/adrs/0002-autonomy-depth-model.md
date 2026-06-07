# ADR 0002: Autonomy and Depth Control Framework

## Status

Accepted — 2026-06-07

## Context

The project was originally classified as `risk_tier: medium` with a hard-coded `autonomy_level: A1` gate that permitted action execution only when the owner explicitly clicked Approve. As the project moves toward a conversational agent architecture (Chunks 23–31), two orthogonal control axes are needed:

1. **Autonomy** — how much the agent can act without an explicit user click
2. **Depth** — how many diagnostic probe layers the agent is permitted to run

Without a formal model, future chunks would hard-code policy in UI or engine code instead of reading a single authoritative setting.

Owner decision on 2026-06-07: `risk_tier` lowered to `low` at governance level 1. The autonomy gate is the compensating control that keeps this acceptable.

## Decision

Define two settings in `project-control.yaml` under `agent_controls`:

### `agent_autonomy_level` (A0–A4)

| Level | Behaviour |
|-------|-----------|
| A0 | Observe only. Agent explains findings; no action execution permitted. |
| A1 | Explicit approval. Agent proposes; owner must click Approve for each action. |
| A2 | Countdown approval. Low-risk actions auto-fire after a 5-second cancelable countdown. Medium/high require explicit approval. |
| A3 | Immediate for low/medium. Low and medium-risk actions fire immediately with a cancel window. High-risk requires explicit approval. |
| A4 | Fully autonomous. All tiers fire without prompting. Reserved for unattended scenarios. |

Default: **A1**.

### `agent_depth_level` (D1–D4)

| Level | Probe scope |
|-------|-------------|
| D1 | Standard surface diagnostics — the existing eight checks. |
| D2 | Adds temperature sensors, NVMe health, top memory/CPU consumers. |
| D3 | Adds dmesg error grouping, device enumeration, boot log summary, display topology. |
| D4 | Reserved for future root-level or firmware probes. |

Default: **D1**.

### Module: `autonomy_controls.py`

Canonical reader for both settings. Exposes:

- `load_autonomy_settings(path)` — returns the parsed dict
- `execution_allowed(path)` — True for A1+; False for A0 (used by execution gates)
- `can_auto_execute(tier, path)` — True if the level auto-fires for the given risk tier (used by Chunk 27 UI)
- `max_depth(path)` — returns the depth integer 1–4 (used by Chunks 24, 30)

### Gate updates

`maintenance_actions._execution_gate` and `ActionPlanRegistry.execute` both call `autonomy_controls.execution_allowed()` so that changing the YAML setting takes effect without a code change.

## Consequences

- A single YAML setting controls agent autonomy across UI, engine, and action runner.
- Depth probes added in Chunks 24 and 30 gate themselves against `max_depth()` — D1 behavior is unchanged at the default setting.
- Future chunks that add autonomy-level-dependent UX (Chunk 27) read `can_auto_execute()` rather than branching on raw string values.
- A0 is a safe fallback: setting `agent_autonomy_level: A0` immediately disables all execution without touching other code.
