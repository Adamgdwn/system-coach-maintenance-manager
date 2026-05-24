# Model Provider Setup

System Coach and Maintenance Manager defaults to local model mode. The preferred path is Ollama with local models such as:

- `qwen3:8b`
- `gemma4:latest`
- `deepseek-r1:14b`
- `gpt-oss:20b`
- `qwen3-vl:8b`

The app also supports two explicit alternatives:

- Bring-your-own-key cloud mode: configure a provider label, API base URL, model name, and the environment variable that contains your API key.
- No-model deterministic fallback: keep all planning and explanations in deterministic local code when no model is available.

## Secrets

Raw API keys are not accepted as saved settings. The provider config stores only the name of an environment variable such as `OPENAI_API_KEY`; the key value must be set outside the app.

Provider settings are stored in a local user config path:

```text
~/.config/system-coach-maintenance-manager/model-providers.json
```

You can override the path with:

```bash
SYSTEM_COACH_MODEL_PROVIDER_CONFIG=/path/to/model-providers.json
```

The config file records provider preferences, not secrets. Local history, reports, action logs, and capability profiles should only expose redacted provider state such as whether an environment variable is present.

## Safety Boundary

Models may classify, explain, summarize, or help reason about evidence. They do not choose executable commands directly. Command selection remains deterministic and guarded by the action contract, catalog, confirmation phrase, server-side plan registry, and execution gates.
