import json
import logging
import os
from pathlib import Path
from typing import Optional

import requests
import openai
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError

from scan2epub.config import AppConfig
from scan2epub.translate.translator import AzureTranslator
from scan2epub.utils.errors import ConfigError, TranslationError

logger = logging.getLogger("scan2epub.azure.preflight")


class PreflightChecker:
    """
    Lightweight application-level Azure preflight checks.
    Only performs minimal, low-cost calls to verify availability/auth.
    """

    def __init__(self, cfg: AppConfig, status_file: Optional[Path] = None) -> None:
        self.cfg = cfg
        self.status_file = status_file

    def _status(self, stage: str, **extras) -> None:
        if not self.status_file:
            return
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with self.status_file.open("a", encoding="utf-8") as f:
                payload = {"t": __import__("time").time(), "event": "preflight", "stage": stage}
                if extras:
                    payload.update(extras)
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ---- Individual service checks ----

    def check_storage(self) -> None:
        self._status("storage_start")
        conn_string = self.cfg.azure_storage.connection_string
        if not conn_string:
            self._status("storage_failed", error="Missing AZURE_STORAGE_CONNECTION_STRING")
            raise ConfigError("Missing AZURE_STORAGE_CONNECTION_STRING for Azure Storage preflight")
        try:
            bsc = BlobServiceClient.from_connection_string(conn_string)
            container = self.cfg.azure_storage.container_name
            cc = bsc.get_container_client(container)
            # exists() is a HEAD call; fast and cheap
            _ = cc.exists()
            self._status("storage_ok", container=container)
        except AzureError as e:
            self._status("storage_failed", error=str(e))
            raise ConfigError(f"Azure Storage preflight failed: {e}") from e
        except Exception as e:
            self._status("storage_failed", error=str(e))
            raise ConfigError(f"Azure Storage preflight failed: {e}") from e

    def check_content_understanding(self) -> None:
        self._status("cu_start")
        endpoint = (self.cfg.azure_cu.endpoint or "").rstrip("/")
        api_key = self.cfg.azure_cu.api_key
        api_version = self.cfg.azure_cu.api_version or "2025-05-01-preview"
        if not endpoint or not api_key:
            self._status("cu_failed", error="Missing AZURE_CU_ENDPOINT or AZURE_CU_API_KEY")
            raise ConfigError("Missing AZURE_CU_ENDPOINT or AZURE_CU_API_KEY for Content Understanding preflight")
        url = f"{endpoint}/contentunderstanding/analyzers"
        try:
            resp = requests.get(
                url,
                params={"api-version": api_version},
                headers={"Ocp-Apim-Subscription-Key": api_key, "Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
                self._status("cu_ok")
            elif resp.status_code in (401, 403, 404):
                self._status("cu_failed", code=resp.status_code, body=resp.text[:200])
                raise ConfigError(f"Content Understanding preflight HTTP {resp.status_code}: {resp.text}")
            else:
                # Treat unexpected as failure to be safe
                self._status("cu_failed", code=resp.status_code, body=resp.text[:200])
                raise ConfigError(f"Content Understanding preflight unexpected HTTP {resp.status_code}: {resp.text}")
        except requests.exceptions.RequestException as e:
            self._status("cu_failed", error=str(e))
            raise ConfigError(f"Content Understanding preflight failed: {e}") from e

    def check_openai(self) -> None:
        self._status("openai_start")
        api_key = self.cfg.azure_openai.api_key
        endpoint = self.cfg.azure_openai.endpoint
        api_version = self.cfg.azure_openai.api_version or "2024-02-15-preview"
        deployment = self.cfg.azure_openai.deployment
        if not all([api_key, endpoint, deployment]):
            self._status("openai_failed", error="Missing Azure OpenAI credentials/deployment")
            raise ConfigError("Missing Azure OpenAI credentials/deployment for OpenAI preflight")
        try:
            client = openai.AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
            # Tiny ping request
            resp = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "ping"},
                    {"role": "user", "content": "ok"},
                ],
                max_tokens=1,
                temperature=0,
            )
            if not getattr(resp, "choices", None):
                self._status("openai_failed", error="No choices in response")
                raise ConfigError("Azure OpenAI preflight returned no choices")
            self._status("openai_ok")
        except Exception as e:
            self._status("openai_failed", error=str(e))
            raise ConfigError(f"Azure OpenAI preflight failed: {e}") from e

    def check_translator(self, to_lang: Optional[str] = None) -> None:
        self._status("translator_start")
        api_key = self.cfg.translator.azure_api_key
        endpoint = (self.cfg.translator.azure_endpoint or "https://api.cognitive.microsofttranslator.com").rstrip("/")
        region = self.cfg.translator.azure_region
        api_version = self.cfg.translator.api_version or "3.0"
        if not api_key:
            self._status("translator_failed", error="Missing AZURE_TRANSLATOR_KEY")
            raise ConfigError("Missing AZURE_TRANSLATOR_KEY for Translator preflight")
        try:
            translator = AzureTranslator(endpoint=endpoint, api_key=api_key, region=region, api_version=api_version)
            translator.preflight_check(to_lang or self.cfg.translator.default_target_language or "en")
            self._status("translator_ok")
        except TranslationError as e:
            self._status("translator_failed", error=str(e))
            raise
        except Exception as e:
            self._status("translator_failed", error=str(e))
            raise TranslationError(f"Translator preflight failed: {e}") from e

    # ---- Convenience orchestrators for CLI paths ----

    def run_for_ocr(self, input_path: str) -> None:
        self._status("preflight_start", services=["storage?" , "cu"])
        # Only check storage if local path (not http(s))
        if not input_path.startswith(("http://", "https://")):
            self.check_storage()
        self.check_content_understanding()
        self._status("preflight_ok", command="ocr")

    def run_for_clean(self, wants_translation: bool = False, translate_to: Optional[str] = None) -> None:
        services = ["openai"] + (["translator"] if wants_translation else [])
        self._status("preflight_start", services=services)
        self.check_openai()
        if wants_translation:
            self.check_translator(translate_to)
        self._status("preflight_ok", command="clean")

    def run_for_convert(self, input_pdf: str, wants_translation: bool = False, translate_to: Optional[str] = None) -> None:
        services = ["storage?" , "cu", "openai"] + (["translator"] if wants_translation else [])
        self._status("preflight_start", services=services)
        if not input_pdf.startswith(("http://", "https://")):
            self.check_storage()
        self.check_content_understanding()
        self.check_openai()
        if wants_translation:
            self.check_translator(translate_to)
        self._status("preflight_ok", command="convert")

    def run_for_translate(self, translate_to: Optional[str] = None) -> None:
        self._status("preflight_start", services=["translator"])
        self.check_translator(translate_to)
        self._status("preflight_ok", command="translate")
