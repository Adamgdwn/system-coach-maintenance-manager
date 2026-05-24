# Release Checklist

Use this checklist before sharing a build with another machine or user.

## Governance

- Run `bash scripts/governance-preflight.sh`.
- Confirm `project-control.yaml` still reflects the current governance level and autonomy level.
- Review `docs/risks/risk-register.md` when adding new diagnostics, request families, history fields, or execution support.
- Confirm machine-changing actions remain approval-required and match the current user-level or elevated execution contracts.

## Automated Validation

- Run `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`.
- Run `python3 -m compileall src tests`.
- Run `git diff --check`.
- Run a basic secret scan before publishing, such as `git grep -nE '(sk-[A-Za-z0-9_-]{12,}|api[_-]?key\\s*[:=]\\s*[^\" ]+|password\\s*[:=])' -- ':!docs/release-checklist.md'`, and review any intentional documentation examples.
- Confirm no local `history/`, provider config, virtual environment, or machine-profile files are staged.

## Public Release Readiness

- Confirm `README.md` includes what the app can and cannot do.
- Confirm `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, and GitHub issue/PR templates are present and match the intended public-sharing model.
- Confirm `.github/workflows/ci.yml` is present and still runs governance, tests, compile checks, browser syntax, secret-pattern scanning, and browser API smoke.
- Confirm public users are told they need local Ollama, their own cloud-provider key, or acceptance of deterministic fallback.
- Confirm `docs/privacy-and-safety.md` describes local collection, optional external model paths, research controls, local history, and secret handling.
- Confirm `docs/public-release-guide.md` gives first-run browser fallback instructions.
- Confirm `docs/public-walkthrough.md` covers first-run discovery, Request Desk, Approval Queue, Pop/COSMIC Agent, and Model Provider Setup.
- Confirm `docs/model-provider-setup.md` says raw API keys are not stored.
- Confirm `docs/action-runner-contract.md` still matches server-side plan registry behavior.
- Confirm the risk register has been reviewed for public sharing, model provider, and action execution risks.

## Linux Native Smoke Test

- Launch with `PYTHONPATH=src python3 -m system_coach_maintenance_manager`.
- Confirm the GTK window opens.
- Run Local Review.
- Run Maintenance Diagnostics.
- Prepare a Request Desk plan.
- Confirm Approval Queue shows exact commands, risk, reversibility, privilege, and guarded execution state.
- Confirm each queued plan shows an action-runner contract and gate reason.
- Refresh History and confirm the local JSONL path is visible.
- Ask Coach a short question when Ollama is available.
- Resize the window below and above the responsive breakpoint.
- Refresh Model Provider health and confirm raw keys are not displayed.

## Browser Fallback Smoke Test

- Launch with `PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser --no-browser`.
- Open the printed local URL.
- Confirm `/health` returns `ok`.
- Run Local Review.
- Run Maintenance Diagnostics.
- Prepare a Request Desk plan.
- Confirm Approval Queue and History update.
- Confirm action execution records completed output for eligible user-level plans, prompts for eligible elevated plans, and blocked reasons for ineligible plans.
- Ask Coach a short question when Ollama is available.
- Confirm Capability Profile and Model Provider Setup render in browser mode.

## Windows Browser Mode Smoke Test

- Launch from PowerShell with `$env:PYTHONPATH="src"; python -m system_coach_maintenance_manager --browser --no-browser`.
- Open the printed local URL.
- Confirm local review, Request Desk, Approval Queue, History, and Coach Chat render.
- Confirm action contracts are visible, user-level execution records output, elevated execution shows the expected OS authorization prompt, and blocked plans show readable reasons.
- Confirm missing Windows diagnostic commands produce readable warnings instead of crashes.
- Confirm bring-your-own-key cloud setup names an environment variable and does not ask for a raw key value.

## Fresh Clone Smoke Test

- Clone the repository into a temporary directory.
- From the fresh clone, run `bash scripts/governance-preflight.sh`.
- Run `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`.
- Run `python3 -m compileall src tests`.
- Launch browser fallback with `PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser --no-browser`.
- Confirm `/health`, `/api/capabilities`, and `/api/model-provider` return JSON without requiring local history or provider config files.

## Packaging

- Confirm `pyproject.toml` includes `src/system_coach_maintenance_manager/web` package data.
- Confirm editable install inside a virtual environment exposes `system-coach`.
- Confirm `system-coach` launches the same CLI as `python -m system_coach_maintenance_manager`.
- Confirm docs mention platform-specific setup paths and Ollama model tags.
- Confirm release notes mention any new model, provider, research, action-runner, or local-history behavior.
