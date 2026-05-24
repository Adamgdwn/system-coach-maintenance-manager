# Public Walkthrough

Use this text walkthrough when screenshots are not available or when validating a fresh clone on a new machine.

## 1. First-Run Discovery

Open browser fallback mode and run Local Review. The first public-user signal should be the Capability Profile. It should name the operating system, distribution or platform, desktop family, display stack, local storage path, available agent surfaces, model-provider state, and recommended docs.

Expected outcome: users can tell whether they are in Linux native mode, Windows browser mode, Pop/COSMIC specialization, local model mode, cloud readiness, or deterministic fallback.

## 2. Request Desk

Type a concrete request such as:

```text
DNS seems broken on my internet.
```

Prepare an approval plan. The result should show family, platform, risk, reversibility, exact commands or manual steps, server plan id, fingerprint, confirmation phrase, and gate reasons.

Expected outcome: users see a plan before anything runs. Unsupported platforms or vague requests become triage records instead of guessed commands.

## 3. Approval Queue

Open Approval Queue after running maintenance diagnostics or Request Desk. Select a plan and review the action contract. Execution requires a registered server plan, exact confirmation phrase, and the command catalog gate.

Expected outcome: runnable plans are visibly different from blocked plans, and blocked plans explain why.

## 4. Pop!_OS + COSMIC Agent

On Pop!_OS or a COSMIC session, open the Pop/COSMIC Agent. Run a standard deep scan, describe the issue, prepare research records, ask the local model, build a fix plan, execute only an eligible approved step, then verify.

Expected outcome: the agent follows scan, identify, assess, analyze, learn, improve, fix, verify. Risky package repair, firmware, OS refresh, purge, broad config deletion, and guessed service restarts remain blocked.

## 5. Model Provider Setup

Open Model Provider Setup. Confirm local model mode, bring-your-own-key cloud mode, and deterministic fallback are shown separately. The cloud panel should show an environment variable name and whether it is present, never the key value.

Expected outcome: users understand they need a local runtime, their own provider key, or acceptance of deterministic fallback behavior.
