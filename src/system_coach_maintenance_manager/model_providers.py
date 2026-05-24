"""Local and bring-your-own model provider setup without storing secrets."""

from __future__ import annotations

from copy import deepcopy
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434"
SUPPORTED_MODES = {"local", "cloud", "deterministic"}
DEFAULT_CONFIG = {
    "active_mode": "local",
    "local": {
        "provider": "ollama",
        "runtime": "ollama",
        "base_url": OLLAMA_URL,
        "preferred_models": [
            "qwen3:8b",
            "qwen3",
            "gemma4:latest",
            "gemma4",
            "deepseek-r1:14b",
            "gpt-oss:20b",
        ],
    },
    "cloud": {
        "enabled": False,
        "provider": "openai-compatible",
        "base_url": "https://api.openai.com/v1",
        "model": "",
        "api_key_env_var": "OPENAI_API_KEY",
    },
    "deterministic": {
        "enabled": True,
    },
}


def provider_config_dir() -> Path:
    configured = os.environ.get("SYSTEM_COACH_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "system-coach-maintenance-manager"


def provider_config_path(config_path: Path | None = None) -> Path:
    if config_path:
        return config_path
    configured = os.environ.get("SYSTEM_COACH_MODEL_PROVIDER_CONFIG")
    if configured:
        return Path(configured).expanduser()
    return provider_config_dir() / "model-providers.json"


def _merge_config(raw: dict | None) -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return config
    active_mode = str(raw.get("active_mode", config["active_mode"])).strip()
    if active_mode in SUPPORTED_MODES:
        config["active_mode"] = active_mode
    for section in ("local", "cloud", "deterministic"):
        if isinstance(raw.get(section), dict):
            config[section].update(raw[section])
    config["cloud"]["api_key_env_var"] = str(config["cloud"].get("api_key_env_var") or "OPENAI_API_KEY").strip()
    config["cloud"]["provider"] = str(config["cloud"].get("provider") or "openai-compatible").strip()
    config["cloud"]["base_url"] = str(config["cloud"].get("base_url") or "").strip()
    config["cloud"]["model"] = str(config["cloud"].get("model") or "").strip()
    config["cloud"]["enabled"] = bool(config["cloud"].get("enabled"))
    config["local"]["provider"] = str(config["local"].get("provider") or "ollama").strip()
    config["local"]["runtime"] = str(config["local"].get("runtime") or "ollama").strip()
    config["local"]["base_url"] = str(config["local"].get("base_url") or OLLAMA_URL).strip()
    preferred = config["local"].get("preferred_models")
    if not isinstance(preferred, list):
        preferred = DEFAULT_CONFIG["local"]["preferred_models"]
    config["local"]["preferred_models"] = [str(model).strip() for model in preferred if str(model).strip()]
    config["deterministic"]["enabled"] = True
    return config


def load_model_provider_config(config_path: Path | None = None) -> dict:
    path = provider_config_path(config_path)
    if not path.exists():
        return _merge_config(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _merge_config(None)
    return _merge_config(raw)


def _saveable_config(payload: dict) -> tuple[dict, list[str]]:
    warnings = []
    def has_raw_key(value: object) -> bool:
        if isinstance(value, dict):
            return any(str(key).lower() == "api_key" or has_raw_key(item) for key, item in value.items())
        if isinstance(value, list):
            return any(has_raw_key(item) for item in value)
        return False

    if has_raw_key(payload):
        warnings.append("Raw API key fields were ignored. Store keys in environment variables instead.")
    config = _merge_config(payload)
    config["cloud"].pop("api_key", None)
    return config, warnings


def save_model_provider_config(payload: dict, config_path: Path | None = None) -> dict:
    config, warnings = _saveable_config(payload)
    path = provider_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return {
        "config": redacted_model_provider_config(config, config_path=path),
        "warnings": warnings,
    }


def redacted_model_provider_config(config: dict | None = None, *, config_path: Path | None = None) -> dict:
    config = _merge_config(config)
    redacted = deepcopy(config)
    env_var = str(redacted["cloud"].get("api_key_env_var") or "").strip()
    redacted["cloud"].pop("api_key", None)
    redacted["cloud"]["api_key_present"] = bool(env_var and os.environ.get(env_var))
    redacted["cloud"]["api_key_storage"] = "environment-variable-only"
    redacted["config_path"] = str(provider_config_path(config_path))
    redacted["secrets_stored"] = False
    return redacted


def _choose_model(models: list[str], preferred: list[str]) -> str | None:
    if not models:
        return None
    for model in preferred:
        if model in models:
            return model
    return models[0]


def _ollama_health(config: dict) -> dict:
    local = config.get("local", {})
    base_url = str(local.get("base_url") or OLLAMA_URL).rstrip("/")
    if local.get("runtime") != "ollama":
        return {
            "available": False,
            "provider": local.get("provider", "local"),
            "runtime": local.get("runtime", "unknown"),
            "models": [],
            "selected_model": None,
            "message": "Only Ollama local runtime health checks are integrated in this release.",
        }
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {
            "available": False,
            "provider": "ollama",
            "runtime": "ollama",
            "models": [],
            "selected_model": None,
            "message": f"Ollama is not reachable at {base_url}: {exc}",
        }
    models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
    selected = _choose_model(models, list(local.get("preferred_models", [])))
    return {
        "available": bool(selected),
        "provider": "ollama",
        "runtime": "ollama",
        "models": models,
        "selected_model": selected,
        "message": f"Using local model {selected} through Ollama." if selected else "Ollama is reachable, but no local models are installed.",
    }


def model_provider_status(config_path: Path | None = None) -> dict:
    config = load_model_provider_config(config_path)
    redacted = redacted_model_provider_config(config, config_path=config_path)
    local = _ollama_health(config)
    cloud = redacted["cloud"]
    cloud_ready = bool(cloud.get("enabled") and cloud.get("api_key_present") and cloud.get("model") and cloud.get("base_url"))
    cloud_message = (
        "BYO-key cloud provider is configured. Prompts may leave the machine only when cloud mode is explicitly selected."
        if cloud_ready
        else "Cloud mode is disabled or missing provider/model/API-key environment configuration."
    )
    modes = [
        {
            "id": "local",
            "label": "Local model mode",
            "available": bool(local.get("available")),
            "requires_external_key": False,
            "message": local.get("message", ""),
            "details": local,
        },
        {
            "id": "cloud",
            "label": "Bring-your-own-key cloud mode",
            "available": cloud_ready,
            "requires_external_key": True,
            "message": cloud_message,
            "details": {
                "provider": cloud.get("provider"),
                "base_url": cloud.get("base_url"),
                "model": cloud.get("model"),
                "api_key_env_var": cloud.get("api_key_env_var"),
                "api_key_present": cloud.get("api_key_present"),
                "api_key_storage": cloud.get("api_key_storage"),
            },
        },
        {
            "id": "deterministic",
            "label": "No-model deterministic fallback",
            "available": True,
            "requires_external_key": False,
            "message": "Deterministic planning remains available without any model provider.",
            "details": {"enabled": True},
        },
    ]
    available_modes = {mode["id"] for mode in modes if mode["available"]}
    active_mode = redacted.get("active_mode", "local")
    effective_mode = active_mode if active_mode in available_modes else "deterministic"
    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "active_mode": active_mode,
        "effective_mode": effective_mode,
        "config": redacted,
        "modes": modes,
        "privacy": "Raw API keys are never stored by this app; cloud keys must come from environment variables.",
        "command_policy": "Model providers may classify, explain, or draft reasoning only. Deterministic guarded planners choose executable commands.",
    }


def configured_ollama_url(config_path: Path | None = None) -> str:
    config = load_model_provider_config(config_path)
    return str(config.get("local", {}).get("base_url") or OLLAMA_URL).rstrip("/")
