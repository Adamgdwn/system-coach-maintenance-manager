# Initial Scope — System Coach and Maintenance Manager

Generated: 2026-04-05

## Classification

| Field          | Value |
|----------------|-------|
| Project name   | System Coach and Maintenance Manager |
| Slug / dir     | system-coach-maintenance-manager |
| Type           | internal-tool |
| Risk tier      | medium |
| Stack          | not specified |
| Primary model  | codex |
| Location       | /home/adamgoodwin/code/agents/system-coach-maintenance-manager |

## Build approach

Primary builder: **codex**

## Scope brief

**Problem:** New users don't always know what has been installed on their system, so we should build a summary and guide that lets the user learn as much as they need.

**User / consumer:** New to intermediate coders and system owners

**MVP:** Functional tool that identifies and coaches users on teh stack, the environments, a few tips and tricks, etc. through a clear GUI

## First session checklist

- [ ] Fill in commands in `AI_BOOTSTRAP.md`
- [ ] Confirm risk tier in `project-control.yaml`
- [ ] Add first ADR if architecture decisions were made at intake
- [ ] Run governance preflight: `bash scripts/governance-preflight.sh`
