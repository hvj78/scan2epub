import json
from pathlib import Path

import pytest

from scan2epub.config import AppConfig
from scan2epub.pipeline import run_translate
from scan2epub.azure.preflight import PreflightChecker
from scan2epub.utils.errors import TranslationError, EPUBError


def test_pipeline_run_translate_hard_stops_on_preflight(monkeypatch, tmp_path: Path):
    """
    run_translate must call AzureTranslator.preflight_check once and hard-stop (raise EPUBError)
    if preflight fails. It should occur before any EPUB reading/writing.
    """
    # Ensure translator key present so code path selects AzureTranslator
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "dummy-key")

    # Monkeypatch preflight_check to raise TranslationError
    import scan2epub.translate.translator as tr_mod
    calls = {"n": 0}

    def fake_preflight(self, to_lang: str, from_lang=None):
        calls["n"] += 1
        raise TranslationError("simulated preflight failure")

    monkeypatch.setattr(tr_mod.AzureTranslator, "preflight_check", fake_preflight, raising=True)

    app_cfg = AppConfig.from_env_and_ini(None)

    # Use dummy paths; preflight should fail before file IO is attempted
    with pytest.raises(EPUBError) as ei:
        run_translate(
            cfg=app_cfg,
            input_epub=str(tmp_path / "in.epub"),
            output_epub=str(tmp_path / "out.epub"),
            to_lang="en",
            provider=None,
            debug=False,
            debug_dir=None,
            status_file=None,
            allow_noop=None,
            min_changed_ratio=None,
        )

    assert "Translator preflight failed" in str(ei.value)
    assert calls["n"] == 1, "preflight must be attempted exactly once"


def test_preflight_checker_status_events_on_translator_failure(monkeypatch, tmp_path: Path):
    """
    PreflightChecker should emit preflight_start and translator_failed events into status JSONL
    when translator preflight fails.
    """
    # Env for key
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "dummy-key")

    # Monkeypatch translator preflight to raise
    import scan2epub.translate.translator as tr_mod

    def fake_preflight(self, to_lang: str, from_lang=None):
        raise TranslationError("boom")

    monkeypatch.setattr(tr_mod.AzureTranslator, "preflight_check", fake_preflight, raising=True)

    app_cfg = AppConfig.from_env_and_ini(None)
    status_file = tmp_path / "status.jsonl"
    pf = PreflightChecker(app_cfg, status_file)

    with pytest.raises(TranslationError):
        pf.run_for_translate(translate_to="en")

    assert status_file.exists()
    lines = [json.loads(l) for l in status_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    events = [(e.get("event"), e.get("stage")) for e in lines]
    assert ("preflight", "preflight_start") in events
    assert ("preflight", "translator_failed") in events
