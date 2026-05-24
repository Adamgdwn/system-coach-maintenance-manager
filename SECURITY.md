# Security Policy

## Reporting Sensitive Issues

Do not open a public issue for a vulnerability that could expose private local data, bypass action execution controls, leak provider secrets, or enable unsafe command execution.

For now, use a minimal private report to the project owner through the contact path provided on the repository profile or by opening a public issue that says only:

```text
I have a private security report for the maintainer.
```

Do not include exploit details, secrets, raw logs, local history, hostnames, private paths, or command output in that public issue.

## Security Boundaries

The expected safety model is:

- executable plans are stored server-side and run by `plan_id`
- direct client-submitted action contracts are not trusted
- exact confirmation phrases are required
- command selection is deterministic and catalog-gated
- model providers may classify, explain, or summarize, but they do not choose executable commands
- elevated actions require operating-system administrator approval
- raw API keys are never stored by the app
- web research is disabled unless project controls and the request both allow it
- local history remains local unless a user intentionally shares it

## What To Avoid Sharing

- API keys, tokens, passwords, cookies, or authorization headers
- unredacted `history/*.jsonl`
- full local logs
- private paths, account names, hostnames, or serial numbers
- screenshots containing personal information
- model-provider config values beyond redacted status

## Supported Versions

This project is currently pre-1.0. Security fixes should target `main` unless the maintainer publishes versioned release branches later.
