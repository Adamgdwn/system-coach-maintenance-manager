# Support

This project is a local-first supervised system coach and maintenance tool. Support works best when reports are small, redacted, and focused on the visible behavior.

## Before Opening An Issue

1. Read `README.md`.
2. Review `docs/public-release-guide.md`.
3. Review `docs/privacy-and-safety.md`.
4. Run browser fallback mode if native GTK setup is uncertain.
5. Check the Capability Profile and Model Provider Setup panels.

## What To Include

- operating system and desktop/session summary
- app mode: browser fallback or native GTK
- the screen or workflow involved
- short reproduction steps
- redacted excerpts of errors or command output
- whether Ollama, BYO-key cloud mode, or deterministic fallback is active

## What Not To Include

- raw `history/*.jsonl`
- API keys or tokens
- raw logs you have not reviewed
- full hostnames, account names, home paths, serial numbers, or private project names
- screenshots with personal data

## Safety Expectations

The app is intentionally supervised. It can inspect, explain, plan, and run eligible guarded actions only after approval. It should not silently repair machines, trust browser-submitted executable contracts, or let model output bypass deterministic command catalogs.
