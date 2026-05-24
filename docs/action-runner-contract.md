# Approved Action Runner Contract

## Current State

The project remains at governance level `1` with autonomy level `A1`. Guarded action execution is enabled only when the user presses Execute and the selected plan passes the action-runner contract.

The Execute button starts the approval event, but execution still requires the selected contract's exact confirmation phrase. It runs exact commands in the guarded catalog only after the phrase matches. Some executable plans apply a current-user setting; others run read-only evidence commands so the next fix is grounded instead of guessed. Elevated plans can request administrator permission through the operating system prompt before running.

The reasoning layer may prepare plans that describe higher-risk, privileged, or broad system changes, but those plans do not automatically become executable. The action-runner contract remains the enforcement boundary between "the app can think through this" and "the app can run this now."

## Contract Fields

Each prepared maintenance or Request Desk plan may include `action_contract`:

- `contract_version`: contract schema name
- `id`: stable action id derived from the plan id
- `plan_id`: source plan id
- `plan_title`: source plan title
- `family`: request or maintenance family
- `status`: current runner status, such as `blocked`, `failed`, or `completed`
- `eligible_for_guarded_execution`: whether the plan shape is narrow enough for guarded execution
- `eligibility_notes`: reasons the plan is not eligible
- `approval_required`: always `true`
- `confirmation_phrase`: exact phrase preserved for audit and future stronger confirmation modes
- `execution_enabled`: `true` only when the plan passes governance, autonomy, catalog, and command checks
- `execution_mode`: `user` for current-user execution or `elevated` for administrator/root execution
- `elevation_prompt`: OS prompt method and message when elevated execution is required
- `execution_gate`: reasons execution is blocked
- `command_preview`: exact command strings from the plan
- `expected_effect`: intended result
- `requires_privilege`: privilege flag
- `reversible`: reversibility flag
- `risk`: risk rating
- `timeout_seconds`: future execution timeout
- `output_capture`: future stdout/stderr capture policy
- `post_check`: checks to perform after a future action
- `rollback`: rollback notes
- `created_at`: contract creation timestamp

## Guarded Candidate Rules

A user-level plan is eligible for guarded execution only when all of these are true:

- approval is required
- risk is `low`
- the plan is reversible
- the plan does not require privilege
- the plan family is in the low-risk guarded catalog
- exact commands are present
- commands do not contain placeholder text such as `<service-name>`
- every command executable is in the guarded catalog

An elevated plan is eligible for guarded execution only when all of these are true:

- approval is required
- the plan requires privilege
- risk is explicitly `low`, `medium`, or `high`
- the plan family is in the elevated guarded catalog
- exact commands are present
- commands do not contain placeholder text such as `<service-name>`
- every command executable is in the guarded catalog

The current low-risk catalog is:

- cursor size
- display brightness
- display dock evidence
- display layout fix
- display night light
- display refresh rate
- display scaling
- audio routing
- failed service evidence
- critical log evidence
- network and DNS evidence

The current elevated catalog is:

- package manager health and package update repair plans
- failed-service and log follow-up plans
- network/DNS plans that require administrator changes
- startup app/service plans that require administrator changes

## Execution Gate

Eligible plans can execute when all gate checks pass:

- governance level `1`
- autonomy level `A1`
- explicit `action_runner_enabled: true` in project controls
- explicit `elevated_action_runner_enabled: true` in project controls for elevated execution
- the Execute button is pressed by the user
- the exact contract confirmation phrase is supplied
- the OS password/UAC prompt is approved for elevated execution
- every command runs through the subprocess runner with `shell=False`, strict timeout, and output capture

On Linux, elevated execution uses `pkexec`, which should show a Polkit password prompt. On Windows, elevated execution uses UAC through PowerShell `Start-Process -Verb RunAs`.

The implementation records completed, failed, and blocked action attempts through the same local history mechanism used for diagnostics and request plans.

## Future Runner Requirements

Before broadening execution:

- reassess project risk, governance level, and autonomy level again
- add post-check execution
- add rollback prompts
- add tests proving unsafe privileged and placeholder commands cannot run
- complete a fresh cold-eyes audit
