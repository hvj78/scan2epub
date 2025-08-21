from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from scan2epub.config_manager import ConfigManager


@dataclass(frozen=True)
class AzureCUConfig:
    """
    Azure Content Understanding (OCR) configuration.
    Note: This keeps only values we actually need in-code; extend when wiring OCR client.
    """
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_version: Optional[str] = None
    # Add other CU specific tunables later as needed


@dataclass(frozen=True)
class AzureOpenAIConfig:
    """
    Azure OpenAI configuration for EPUB cleaning LLM.
    Only defines placeholders for now to avoid tight coupling with client construction.
    """
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_version: Optional[str] = None
    deployment: Optional[str] = None
    # Extend when wiring cleaner to use DI with a client provider


@dataclass(frozen=True)
class AzureStorageConfig:
    """
    Azure Blob Storage configuration for temporary uploads (local PDF -> SAS URL).
    """
    connection_string: str
    container_name: str
    sas_token_expiry_hours: int
    max_file_size_bytes: int
    log_cleanup: bool
    debug: bool


@dataclass(frozen=True)
class TranslatorConfig:
    """
    Translation configuration (provider + Azure Translator settings).
    """
    provider: str
    default_target_language: str
    azure_endpoint: Optional[str] = None
    azure_region: Optional[str] = None
    azure_api_key: Optional[str] = None
    api_version: str = "3.0"
    # Quality guardrails
    allow_noop: bool = False
    min_changed_ratio: float = 0.0


@dataclass(frozen=True)
class ProcessingConfig:
    """
    Application processing preferences and toggles coming from INI defaults and CLI flags.
    """
    debug: bool
    save_interim: bool
    cleanup_on_failure: bool


@dataclass(frozen=True)
class DiagnosticsConfig:
    """
    Diagnostics and preflight behavior settings.
    """
    skip_preflight: bool = False


@dataclass(frozen=True)
class AppConfig:
    """
    Root typed configuration passed across CLI -> pipeline -> services.
    All env reads are centralized here; library code should receive sub-configs explicitly.
    """
    azure_cu: AzureCUConfig
    azure_openai: AzureOpenAIConfig
    azure_storage: AzureStorageConfig
    translator: TranslatorConfig
    processing: ProcessingConfig
    diagnostics: DiagnosticsConfig

    @staticmethod
    def _get_env_str(name: str, default: Optional[str] = None) -> Optional[str]:
        v = os.getenv(name)
        if v is None or v == "":
            return default
        return v

    @staticmethod
    def _get_env_int(name: str, default: Optional[int] = None) -> Optional[int]:
        v = os.getenv(name)
        if v is None or v == "":
            return default
        try:
            return int(v)
        except ValueError:
            return default

    @classmethod
    def from_env_and_ini(cls, ini_path: Optional[str]) -> "AppConfig":
        """
        Build AppConfig from environment variables (already loaded by CLI via load_dotenv())
        and INI defaults via ConfigManager.

        Precedence (highest -> lowest) for booleans/values we expose:
        - CLI (handled in cli.py)
        - INI via ConfigManager
        - Environment (for secrets and endpoints)
        - Hardcoded defaults where appropriate
        """
        cfg = ConfigManager(ini_path)

        # Azure CU (OCR) - leave optional for now; validation can occur when feature is used
        cu = AzureCUConfig(
            endpoint=cls._get_env_str("AZURE_CU_ENDPOINT"),
            api_key=cls._get_env_str("AZURE_CU_API_KEY"),
            api_version=cls._get_env_str("AZURE_CU_API_VERSION"),
        )

        # Azure OpenAI - used by cleaner
        aoi = AzureOpenAIConfig(
            endpoint=cls._get_env_str("AZURE_OPENAI_ENDPOINT"),
            api_key=cls._get_env_str("AZURE_OPENAI_API_KEY"),
            api_version=cls._get_env_str("AZURE_OPENAI_API_VERSION"),
            deployment=cls._get_env_str("AZURE_OPENAI_DEPLOYMENT_NAME"),
        )

        # Azure Storage
        connection_string = cls._get_env_str("AZURE_STORAGE_CONNECTION_STRING", "") or ""
        # container name and limits from INI defaults
        storage = AzureStorageConfig(
            connection_string=connection_string,
            container_name=cfg.blob_container_name,
            sas_token_expiry_hours=cfg.sas_token_expiry_hours,
            max_file_size_bytes=cfg.max_file_size_bytes,
            log_cleanup=cfg.log_cleanup,
            debug=cfg.debug,
        )

        # Translator (provider + Azure Translator settings; env can override endpoint/region/key)
        translator = TranslatorConfig(
            provider=cfg.translator_provider,
            default_target_language=cfg.default_target_language,
            azure_endpoint=cls._get_env_str("AZURE_TRANSLATOR_ENDPOINT") or cfg.azure_translator_endpoint,
            azure_region=cls._get_env_str("AZURE_TRANSLATOR_REGION") or cfg.azure_translator_region,
            azure_api_key=cls._get_env_str("AZURE_TRANSLATOR_KEY"),
            api_version=cfg.azure_translator_api_version,
            allow_noop=cfg.translator_allow_noop,
            min_changed_ratio=cfg.translator_min_changed_ratio,
        )

        # Processing toggles (CLI may override these when building debug/save_interim)
        processing = ProcessingConfig(
            debug=cfg.debug,
            save_interim=cfg.save_interim,
            cleanup_on_failure=getattr(cfg, "cleanup_on_failure", True),
        )

        diagnostics = DiagnosticsConfig(
            skip_preflight=cfg.skip_preflight,
        )

        return cls(
            azure_cu=cu,
            azure_openai=aoi,
            azure_storage=storage,
            translator=translator,
            processing=processing,
            diagnostics=diagnostics,
        )
