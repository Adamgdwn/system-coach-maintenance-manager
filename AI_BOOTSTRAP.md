# AI Bootstrap Rules

## Purpose
This repository must be workable by Claude, Codex, and local coding agents
using the same operating rules.

## Change rules
- Prefer editing existing files over creating duplicate replacements.
- Keep changes small and reversible.
- Do not rename or move core files unless explicitly instructed.
- Explain new dependencies before adding them.
- Update docs when behavior, interfaces, or architecture change.

## Governance
- Run the governance preflight before making substantial changes:
  `bash scripts/governance-preflight.sh`
- Review `project-control.yaml` for risk tier and required controls.
- Record deviations as exceptions rather than ignoring them.

## Commands
- Install: `bash launchers/install-desktop-entry.sh`
- Dev:     `PYTHONPATH=src python3 -m system_coach_maintenance_manager`
- Lint:    `python3 -m compileall src tests`
- Build:   `python3 -m compileall src`
- Test:    `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`

## Document control
- Architecture decisions go in `docs/`
- If code behavior changes, update the nearest controlled document in the same task

## Completion standard
A task is not complete until relevant validation is run or a blocker is clearly stated.

## Day Closeout

When Adam or an agent discusses locking down, closing out, wrapping the day,
stopping for the night, or handing off before a break, update the shared work
ledger as a required final step before the last response:

1. Update `/home/adamgoodwin/code/01 Work Tracking/system-coach-maintenance-manager/latest.md`
2. Add today's entry at the **top** of `/home/adamgoodwin/code/01 Work Tracking/system-coach-maintenance-manager/log/YYYY-MM-DD.md`
3. Update `/home/adamgoodwin/code/01 Work Tracking/01 Work Tracking/latest.md`
4. Add an entry at the top of `/home/adamgoodwin/code/01 Work Tracking/01 Work Tracking/log/YYYY-MM-DD.md`
5. Follow the format and rules in `/home/adamgoodwin/code/01 Work Tracking/README.md`
6. State in the final response that work tracking was updated.
