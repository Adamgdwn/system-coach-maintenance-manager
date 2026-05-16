# Change Log

## Unreleased

- Completed roadmap Chunk 1 by refreshing governance risk documentation, closing stale external governance-path language, and cleaning duplicate architecture wording.
- Completed roadmap Chunk 2 by splitting maintenance plans into Linux, Windows, and explicit triage branches with tests for platform-specific command families.
- Added desktop-session context to maintenance diagnostics and passed OS/desktop hints into Request Desk planning from desktop and browser mode.
- Added governance level metadata and required manual/roadmap docs for New Build Agent preflight compatibility.
- Added a local governance checker so `bash scripts/governance-preflight.sh` works without external environment setup.
- Changed the preferred local coaching model to `gemma4:latest`, with prior models kept as fallbacks.
- Added a maintenance-manager planning document that adapts useful Chuwi Optimizer patterns while excluding autonomous fixer behavior.
- Added read-only maintenance diagnostics, ranked findings, approval-required plan previews, and desktop/browser/AI/export integration.
- Added a Request Desk for platform-aware approval plans, starting with cursor/pointer size changes on Linux and Windows.
- Added browser fallback Coach Chat so Windows and Linux browser-mode users can ask the local model with current context.
- Made browser mode import lazily so Windows systems can launch without GTK.
- Built the first working System Stack Review and Coach application.
- Added a local web GUI with learner-friendly stack reporting and compatibility notes.
- Added bounded local probe agents for environment and toolchain inspection.
- Added an opt-in filesystem mapper for selected roots with project and config discovery.
- Added a share-summary action for local findings.
- Converted the primary interface from browser-first to a native GTK desktop shell.
- Added an interactive Ask The Coach workflow powered by a local Ollama model.
- Added stronger scan warnings and local AI status handling.
- Made the native desktop shell adapt more cleanly to narrow and wide window sizes.
- Configured persistent local governance path setup and closed the governance preflight exception.
- Added launcher scripts for direct execution and desktop installation.
- Added architecture, deployment, runbook, ADR, and exception documentation for the first release.
