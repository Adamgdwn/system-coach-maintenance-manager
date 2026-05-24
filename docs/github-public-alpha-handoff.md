# GitHub Public Alpha Handoff

This document captures the public GitHub posture for this repository and provides a reusable template for preparing similar repositories for public alpha release.

## Current Repository State

- Repository: `https://github.com/Adamgdwn/system-coach-maintenance-manager`
- Default branch: `main`
- Visibility: public
- License: MIT
- Current alpha release: `v0.1.0-alpha`
- Release URL: `https://github.com/Adamgdwn/system-coach-maintenance-manager/releases/tag/v0.1.0-alpha`
- Release commit: `69acc82 Prepare GitHub public alpha landing`
- CI workflow: `.github/workflows/ci.yml`
- Required branch check: `validation`
- Branch protection:
  - requires the `validation` status check
  - requires the branch to be up to date before merge
  - blocks force pushes
  - blocks branch deletion
  - does not enforce admin lockout, so the owner keeps emergency maintainer control

## GitHub About Settings

Current repository description:

```text
Local-first system coach for understanding, diagnosing, and safely maintaining Linux desktops.
```

Current topics:

```text
ai-agent
cosmic-desktop
gtk
linux
local-first
maintenance
ollama
pop-os
python
system-diagnostics
```

For another repository, use topics that describe the actual platform, audience, runtime, and risk model. Avoid aspirational tags that imply support the project does not yet provide.

## Public Landing Materials

The GitHub landing page is supported by:

- `README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `.github/ISSUE_TEMPLATE/`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/ci.yml`
- `docs/public-release-guide.md`
- `docs/privacy-and-safety.md`
- `docs/release-checklist.md`
- `docs/releases/v0.1.0-alpha.md`
- `docs/assets/screenshots/`

The README should answer five questions quickly:

1. What is this?
2. Who is it for?
3. What can it do?
4. What will it not do?
5. How does a new user try it safely?

## User-Facing Caveats

Keep these caveats visible in README, release notes, support templates, and safety docs:

- This is public alpha software.
- It is supervised local maintenance software, not an unattended repair bot.
- Users must review command previews, confirmation phrases, fingerprints, rollback notes, and verification steps before approving actions.
- Browser/client payloads are not trusted as executable action contracts.
- Model output may explain, classify, or reason, but deterministic guarded planners choose executable commands.
- Raw API keys are not accepted or stored by the app.
- Cloud model use is bring-your-own-key only.
- Local history, logs, screenshots, hostnames, account names, private paths, serial numbers, and command output must be reviewed and redacted before public sharing.
- Platform-specific features should say where they are strongest and how they degrade elsewhere.

## Risk Management Pattern

Use this pattern when publicizing any local agent, maintenance, diagnostics, or automation repository:

1. Describe the trust boundary in plain language.
2. State what the app refuses to do.
3. Make secrets and local data handling explicit.
4. Keep support intake structured through issue templates.
5. Run CI on every push and pull request.
6. Add a release checklist that includes secret scanning and fresh-clone smoke tests.
7. Sanitize screenshots before committing them.
8. Create prerelease notes that repeat safety boundaries.
9. Add branch protection only after CI exists and has passed at least once.
10. Keep maintainer emergency control unless the project is ready for stricter governance.

## Reusable Public Alpha Checklist

Use this checklist before making another repository public or announcing a public alpha.

### Repository Basics

- Set the GitHub About description.
- Add accurate topics.
- Confirm the default branch is correct.
- Choose the license intentionally.
- Confirm `README.md` explains purpose, status, caveats, install, first run, validation, support, and docs.
- Add `SECURITY.md`, `SUPPORT.md`, and `CONTRIBUTING.md`.
- Add issue templates for bug reports, safety/privacy concerns, and feature requests.
- Add a pull request template with risk and validation checkboxes.

### CI And Controls

- Add GitHub Actions for the checks the project can actually run in a clean environment.
- Include governance or policy checks where applicable.
- Include tests, compile/syntax checks, whitespace checks, and secret-pattern scanning.
- Add a smoke test for the lowest-friction user entry point.
- Wait for CI to pass on `main`.
- Add branch protection requiring the CI check.

### Screenshots And Assets

- Capture real screenshots from the app or tool.
- Review screenshots for usernames, hostnames, private paths, secrets, tokens, raw logs, private projects, serial numbers, and personal data.
- Prefer sanitized example state over live machine health details.
- Commit screenshots under `docs/assets/screenshots/`.
- Reference screenshots from `README.md`.

### Release Notes

- Create a prerelease tag for alpha software.
- Use release notes that include:
  - what works
  - what is intentionally blocked
  - how to run it
  - validation performed
  - privacy and safety caveats
  - support/reporting boundaries
- Attach useful screenshots or small assets when they make evaluation easier.

### Final Verification

Run local validation:

```bash
bash scripts/governance-preflight.sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall src tests
git diff --check
```

Run a secret scan with repo-specific exclusions for intentional documentation examples:

```bash
! git grep -nE '(sk-[A-Za-z0-9_-]{12,}|api[_-]?key\s*[:=]\s*[^" ]+|password\s*[:=])'
```

Run a smoke test for the main user entry point. For this repository:

```bash
PYTHONPATH=src python3 -m system_coach_maintenance_manager --browser --no-browser
```

Then verify:

```bash
curl -fsS "$url/health"
curl -fsS "$url/api/capabilities"
curl -fsS "$url/api/model-provider"
```

## GitHub Commands Used

Set repository metadata:

```bash
gh repo edit Adamgdwn/system-coach-maintenance-manager \
  --description "Local-first system coach for understanding, diagnosing, and safely maintaining Linux desktops." \
  --add-topic pop-os \
  --add-topic cosmic-desktop \
  --add-topic linux \
  --add-topic ollama \
  --add-topic local-first \
  --add-topic maintenance \
  --add-topic system-diagnostics \
  --add-topic ai-agent \
  --add-topic python \
  --add-topic gtk \
  --enable-issues \
  --enable-wiki=false
```

Create the alpha release:

```bash
gh release create v0.1.0-alpha docs/assets/screenshots/*.png \
  --repo Adamgdwn/system-coach-maintenance-manager \
  --target main \
  --title "System Coach Maintenance Manager v0.1.0-alpha" \
  --notes-file docs/releases/v0.1.0-alpha.md \
  --prerelease
```

Apply branch protection:

```bash
cat > /tmp/system-coach-main-protection.json <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["validation"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON

gh api --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/Adamgdwn/system-coach-maintenance-manager/branches/main/protection \
  --input /tmp/system-coach-main-protection.json
```

For another repository, replace owner, repo, branch, status-check context, tag, release title, and asset paths.

## Handoff Notes

This repository is now suitable to use as a public-alpha template for similar local-first tools. Before copying the pattern to another repo, revisit:

- license choice
- real project risk level
- data sensitivity
- whether external services are involved
- whether actions can change a user's machine
- whether screenshots are sanitized
- whether CI can run reliably on GitHub-hosted runners
- whether branch protection should enforce admins or require pull-request reviews

The template is intentionally conservative for agentic/local-maintenance projects: explain the boundaries first, make safe first-run behavior easy, and put risk controls in both docs and automation.
