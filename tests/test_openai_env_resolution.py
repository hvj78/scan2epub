import os
import pytest

from scan2epub.config import AppConfig


def test_uses_AZURE_OPENAI_DEPLOYMENT_NAME(monkeypatch):
    # Ensure a clean environment for these vars
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_NAME", raising=False)

    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "dep_a")

    app = AppConfig.from_env_and_ini(None)
    assert app.azure_openai.deployment == "dep_a"
