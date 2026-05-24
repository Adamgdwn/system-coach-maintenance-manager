import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from system_coach_maintenance_manager.model_providers import (
    load_model_provider_config,
    model_provider_status,
    save_model_provider_config,
)


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ModelProviderTests(unittest.TestCase):
    def test_default_status_prefers_local_when_ollama_has_supported_model(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"SYSTEM_COACH_MODEL_PROVIDER_CONFIG": str(Path(tmp) / "providers.json")},
            clear=True,
        ), patch(
            "system_coach_maintenance_manager.model_providers.urllib.request.urlopen",
            return_value=_FakeResponse({"models": [{"name": "qwen3:8b"}]}),
        ):
            status = model_provider_status()

        self.assertEqual(status["active_mode"], "local")
        self.assertEqual(status["effective_mode"], "local")
        self.assertFalse(status["config"]["secrets_stored"])
        self.assertTrue(any(mode["id"] == "deterministic" and mode["available"] for mode in status["modes"]))

    def test_unavailable_local_model_falls_back_to_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"SYSTEM_COACH_MODEL_PROVIDER_CONFIG": str(Path(tmp) / "providers.json")},
            clear=True,
        ), patch(
            "system_coach_maintenance_manager.model_providers.urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            status = model_provider_status()

        self.assertEqual(status["active_mode"], "local")
        self.assertEqual(status["effective_mode"], "deterministic")

    def test_saving_cloud_provider_never_persists_or_returns_raw_api_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {
                "SYSTEM_COACH_MODEL_PROVIDER_CONFIG": str(Path(tmp) / "providers.json"),
                "SYSTEM_COACH_OPENAI_KEY": "sk-test-secret",
            },
            clear=True,
        ), patch(
            "system_coach_maintenance_manager.model_providers.urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            result = save_model_provider_config(
                {
                    "active_mode": "cloud",
                    "cloud": {
                        "enabled": True,
                        "provider": "openai-compatible",
                        "base_url": "https://api.openai.com/v1",
                        "model": "example-model",
                        "api_key_env_var": "SYSTEM_COACH_OPENAI_KEY",
                        "api_key": "sk-should-not-save",
                    },
                }
            )
            saved = Path(tmp) / "providers.json"
            raw_text = saved.read_text(encoding="utf-8")
            loaded = load_model_provider_config(saved)
            status = model_provider_status(saved)

        self.assertIn("Raw API key fields were ignored", result["warnings"][0])
        self.assertNotIn("sk-should-not-save", raw_text)
        self.assertNotIn("api_key", loaded["cloud"])
        self.assertTrue(status["config"]["cloud"]["api_key_present"])
        self.assertEqual(status["effective_mode"], "cloud")
        self.assertNotIn("sk-test-secret", json.dumps(status))


if __name__ == "__main__":
    unittest.main()
