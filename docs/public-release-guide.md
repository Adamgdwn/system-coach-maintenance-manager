# Public GitHub Release Guide

This project is safe to share as a local-first supervised maintenance tool when the release checklist passes. Public users should assume the app is inspecting an unknown machine and should start in browser fallback mode unless they already have Linux GTK dependencies installed.

## What This Can Do

- Inspect the local machine with bounded read-only probes.
- Explain installed tools, likely stack patterns, and selected filesystem roots.
- Run read-only maintenance diagnostics.
- Prepare approval-required Request Desk plans.
- Execute only guarded, catalogued actions after the user approves the exact plan and confirmation phrase.
- Use local Ollama models when available.
- Use bring-your-own-key cloud mode only when the user configures a provider and key environment variable.
- Fall back to deterministic no-model behavior when no model is available.
- Specialize for Pop!_OS + COSMIC when Pop/COSMIC signals are detected.

## What This Cannot Do

- It does not run hidden autonomous repairs.
- It does not execute client-submitted action contracts.
- It does not invent executable commands from model output.
- It does not ship API keys, shared tokens, or owner-funded cloud access.
- It does not upload local logs or filesystem maps by default.
- It does not make destructive package, firmware, OS refresh, purge, broad config deletion, or guessed service restart actions executable in the Pop/COSMIC agent slice.

## First Run

1. Clone the repository.
2. Read `README.md`, `docs/setup-linux.md`, or `docs/setup-windows-browser.md`.
3. Start browser fallback mode:

   ```bash
   PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser --no-browser
   ```

4. Open the printed local URL.
5. Review the Capability Profile.
6. Choose a model path:
   - local Ollama model mode
   - bring-your-own-key cloud mode
   - deterministic no-model fallback
7. Run Local Review.
8. Run Maintenance Diagnostics.
9. Use Request Desk or the Pop/COSMIC Agent only after reviewing the capability profile and approval gates.

## Public Support Boundaries

Ask users to share summaries intentionally. They should not paste full local history, raw logs, model-provider configs, or command outputs into public issues unless they have reviewed them for private paths, hostnames, account names, tokens, and sensitive machine details.
