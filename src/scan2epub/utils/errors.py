class Scan2EpubError(Exception):
    """Base exception for scan2epub."""


class ConfigError(Scan2EpubError):
    """Configuration related errors."""


class StorageError(Scan2EpubError):
    """Azure storage related errors."""


class OCRError(Scan2EpubError):
    """OCR processing related errors."""


class LLMError(Scan2EpubError):
    """LLM cleanup related errors."""


class EPUBError(Scan2EpubError):
    """EPUB building/processing related errors."""
