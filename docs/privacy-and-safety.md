# Privacy And Safety Model

System Coach and Maintenance Manager is local-first and supervised. Its default behavior is to inspect, explain, plan, and record locally.

## Local Data

The app may collect:

- operating system and desktop/session details
- installed command/tool availability and versions
- bounded command output from read-only diagnostics
- user-selected filesystem root summaries
- maintenance findings and request-plan previews
- action results for approved, failed, or blocked attempts
- Pop/COSMIC lesson records and research metadata
- model-provider readiness state

Local history is stored under `history/` by default or the configured `SYSTEM_COACH_HISTORY_DIR`. Model provider preferences are stored in the user config path or `SYSTEM_COACH_MODEL_PROVIDER_CONFIG`. Machine-specific state should not be committed to the repository.

## Data That May Leave The Machine

Nothing leaves the machine by default except when the user enables an external path:

- Local Ollama mode sends prompts to the local Ollama API on the configured local URL.
- Bring-your-own-key cloud mode may send prompts and selected context to the configured provider after the user explicitly enables it.
- Pop/COSMIC live web research is disabled unless project controls enable it and the request opts in. Safe research queries use sanitized symptom/profile facts, not raw logs.

## Secrets

Raw API keys are never saved by the app. Model provider setup stores only an environment variable name such as `OPENAI_API_KEY`. Reports, history, provider status, and capability profiles should expose only whether that environment variable is present.

## Action Safety

Executable actions are governed by several gates:

- plans are approval-required
- executable contracts are stored server-side and executed by `plan_id`
- confirmation phrases must match exactly
- commands must come from deterministic guarded catalogs
- models may classify or explain but cannot provide executable commands
- elevated actions require OS administrator approval
- blocked destructive actions are shown as human escalation paths, not executable plans

## User Controls

Users can avoid external model calls by selecting deterministic fallback mode or local model mode without cloud configuration. Users can avoid live research by leaving `pop_cosmic_agent.web_research_enabled` disabled in `project-control.yaml`. Users can move local history and provider config paths with environment variables before launching the app.
