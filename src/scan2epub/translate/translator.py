import logging
import time
from typing import List, Optional, Protocol, runtime_checkable, Iterable

import requests

from scan2epub.utils.errors import TranslationError

logger = logging.getLogger("scan2epub.translate")


@runtime_checkable
class ITranslator(Protocol):
    """
    Translation provider interface.
    Implementations should preserve input ordering and return one translated string per input segment.
    """

    def translate_text(self, segments: List[str], to_lang: str, from_lang: Optional[str] = None) -> List[str]:
        ...


class AzureTranslator(ITranslator):
    """
    Microsoft Translator Text API (Cognitive Services) implementation.

    API Reference:
    - Endpoint: {endpoint}/translate?api-version=3.0&to={to}&from={from?}
    - Docs: https://learn.microsoft.com/azure/ai-services/translator/reference/v3-0-translate
    """

    # Conservative limits (actual service limits are higher; keep headroom to avoid 413)
    MAX_DOCS_PER_REQUEST = 90
    MAX_CHARS_PER_REQUEST = 45000  # total of "Text" fields per request

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        region: Optional[str] = None,
        api_version: str = "3.0",
        session: Optional[requests.Session] = None,
        timeout_s: int = 30,
        max_retries: int = 3,
        retry_delay_s: int = 2,
    ) -> None:
        if not endpoint or not api_key:
            raise TranslationError("AzureTranslator requires endpoint and api_key")
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.region = region
        self.api_version = api_version
        self.session = session or requests.Session()
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.retry_delay_s = retry_delay_s

    def _headers(self) -> dict:
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json; charset=utf-8",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        return headers

    def _batch_segments(self, segments: List[str]) -> Iterable[List[str]]:
        """
        Yield batches of segments such that each batch has <= MAX_DOCS_PER_REQUEST and total chars under limit.
        """
        batch: List[str] = []
        chars = 0
        for s in segments:
            s_len = len(s or "")
            if (
                batch
                and (len(batch) + 1 > self.MAX_DOCS_PER_REQUEST or chars + s_len > self.MAX_CHARS_PER_REQUEST)
            ):
                yield batch
                batch = [s]
                chars = s_len
            else:
                batch.append(s)
                chars += s_len
        if batch:
            yield batch

    def preflight_check(self, to_lang: str, from_lang: Optional[str] = None) -> None:
        """
        Lightweight availability/auth check. Performs a single tiny translation request with NO retries.
        Raises TranslationError on any non-2xx or unexpected response shape.
        """
        url = f"{self.endpoint}/translate"
        params = {"api-version": self.api_version, "to": (to_lang or "en")}
        if from_lang:
            params["from"] = from_lang
        body = [{"Text": "ping"}]
        try:
            resp = self.session.post(
                url,
                params=params,
                json=body,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text
                raise TranslationError(f"Translator preflight HTTP {resp.status_code}: {err_body}")
            data = resp.json()
            # Expect a non-empty list, first item should have 'translations' with at least one entry
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                raise TranslationError("Translator preflight returned unexpected response")
            translations = data[0].get("translations", [])
            if not translations:
                raise TranslationError("Translator preflight returned no translations")
        except requests.RequestException as e:
            raise TranslationError(f"Translator preflight failed: {e}") from e

    def translate_text(self, segments: List[str], to_lang: str, from_lang: Optional[str] = None) -> List[str]:
        if not segments:
            return []
        if not to_lang or len(to_lang) < 2:
            raise TranslationError("Target language code (to_lang) must be provided")

        url = f"{self.endpoint}/translate"
        params = {"api-version": self.api_version, "to": to_lang}
        if from_lang:
            params["from"] = from_lang

        translated: List[str] = []
        for batch_idx, batch in enumerate(self._batch_segments(segments), start=1):
            body = [{"Text": s} for s in batch]
            attempt = 0
            last_err: Optional[str] = None
            while attempt < self.max_retries:
                attempt += 1
                try:
                    resp = self.session.post(
                        url,
                        params=params,
                        json=body,
                        headers=self._headers(),
                        timeout=self.timeout_s,
                    )
                    if resp.status_code >= 400:
                        # include response body for diagnostics
                        try:
                            err_body = resp.json()
                        except Exception:
                            err_body = resp.text
                        raise TranslationError(
                            f"Azure Translator HTTP {resp.status_code}: {err_body}"
                        )
                    data = resp.json()
                    # Response is a list with same length as body; each element has 'translations' list
                    # Map to first translation text per item
                    batch_out: List[str] = []
                    for i, item in enumerate(data):
                        translations = item.get("translations", [])
                        if not translations:
                            # preserve index alignment; fallback to original if missing
                            logger.warning(f"No translation returned for item {i} in batch {batch_idx}; using original")
                            batch_out.append(batch[i])
                        else:
                            batch_out.append((translations[0].get("text") or "").strip())
                    translated.extend(batch_out)
                    break  # batch succeeded
                except Exception as e:
                    last_err = str(e)
                    if attempt < self.max_retries:
                        backoff = self.retry_delay_s * attempt
                        logger.warning(
                            f"Azure Translator batch {batch_idx} failed (attempt {attempt}/{self.max_retries}): {last_err}. Retrying in {backoff}s"
                        )
                        time.sleep(backoff)
                    else:
                        # On final failure, degrade gracefully: append originals for this batch
                        logger.error(
                            f"Azure Translator batch {batch_idx} failed after retries: {last_err}. Using original text for this batch."
                        )
                        translated.extend(batch)
                        break

        # Ensure alignment
        if len(translated) != len(segments):
            # This should not happen, but guard against API anomalies
            logger.error(
                f"Translated segments count mismatch: expected {len(segments)}, got {len(translated)}. Truncating/patching."
            )
            # Patch by trimming or extending with originals
            if len(translated) > len(segments):
                translated = translated[: len(segments)]
            else:
                translated.extend(segments[len(translated) :])

        return translated


__all__ = ["ITranslator", "AzureTranslator"]
