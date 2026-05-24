# Contributing

Thank you for helping improve System Coach and Maintenance Manager. Contributions should preserve the local-first, supervised safety model.

## Ground Rules

- Keep local inspection bounded and explainable.
- Do not add bundled API keys, sample real secrets, shared tokens, or owner-funded cloud credentials.
- Do not make model output authoritative for executable commands.
- Keep executable plans deterministic, catalog-gated, confirmation-required, and server-side plan based.
- Keep elevated actions explicit and OS-approved.
- Document any new data collection, web/cloud behavior, history field, or execution path.
- Add tests for new request families, platform behavior, provider settings, or action contracts.

## Development Checks

Run these before proposing changes:

```bash
bash scripts/governance-preflight.sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall src tests
git diff --check
```

For UI/API changes, also run browser fallback mode and check `/health`, `/api/capabilities`, and `/api/model-provider`.

## Public Safety Review

Changes need extra care when they touch:

- action execution
- elevated permissions
- model providers or BYO-key handling
- local history
- filesystem mapping
- Pop/COSMIC research
- web/cloud behavior
- support templates or docs that encourage sharing machine data

Use `docs/privacy-and-safety.md`, `docs/action-runner-contract.md`, and `docs/release-checklist.md` as the baseline.
