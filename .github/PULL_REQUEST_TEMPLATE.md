## Summary

- 

## Risk Area

- [ ] Documentation only
- [ ] Read-only local inspection
- [ ] Request planning
- [ ] Guarded user-level execution
- [ ] Elevated execution
- [ ] Model provider / BYO-key handling
- [ ] Pop/COSMIC research or agent behavior
- [ ] Local history / privacy

## Safety Checklist

- [ ] I did not add bundled API keys, shared tokens, sample real secrets, or owner-funded cloud credentials.
- [ ] I did not make model output authoritative for executable commands.
- [ ] Any executable action remains deterministic, catalog-gated, previewed, confirmation-required, and server-side plan based.
- [ ] Any new local data collection is documented and bounded.
- [ ] Any web/cloud behavior is opt-in and documented.
- [ ] Docs mention user-facing caveats where behavior changed.

## Validation

- [ ] `bash scripts/governance-preflight.sh`
- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
- [ ] `python3 -m compileall src tests`
- [ ] `git diff --check`
- [ ] Browser fallback smoke if UI/API changed
- [ ] Secret scan if provider, docs, logs, history, or examples changed
