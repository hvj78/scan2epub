import logging
import os
import re
import json
import time
import zipfile
import tempfile
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable, Any
from dataclasses import dataclass

import openai
from bs4 import BeautifulSoup
from ebooklib import epub

from scan2epub.utils.errors import LLMError, EPUBError
from scan2epub.config import AzureOpenAIConfig


logger = logging.getLogger("scan2epub.cleaner")


@dataclass
class CleanerRuntimeConfig:
    """Cleaner runtime tuning parameters (kept local to avoid expanding AppConfig yet)."""
    max_tokens_per_chunk: int = 3000
    temperature: float = 0.1
    max_tokens_response: int = 4000
    max_retries: int = 3
    retry_delay: int = 2


# -------- Progress reporting --------

class ProgressReporter:
    """Interface for reporting progress; methods are no-ops by default."""
    def on_stage(self, stage: str, extras: Optional[Dict[str, Any]] = None) -> None: ...
    def on_chunking_done(self, total_chunks: int) -> None: ...
    def on_chunk_start(self, idx: int, total: int) -> None: ...
    def on_llm_submit(self, idx: int, total: int) -> None: ...
    def on_llm_wait_start(self, idx: int, total: int) -> None: ...
    def on_llm_wait_heartbeat(self, idx: int, total: int, elapsed_s: int) -> None: ...
    def on_llm_wait_end(self, idx: int, total: int, latency_s: float) -> None: ...
    def on_chunk_result(self, idx: int, total: int, tokens_in: Optional[int], tokens_out: Optional[int], latency_s: float) -> None: ...
    def on_retry(self, idx: int, attempt: int, max_attempts: int, backoff_s: int, error: str) -> None: ...
    def on_error_giveup(self, idx: int, error: str) -> None: ...
    def on_summary(self, total: int, retries: int, tokens_in: Optional[int], tokens_out: Optional[int], elapsed_s: int) -> None: ...


class ConsoleProgressReporter(ProgressReporter):
    def __init__(self, logger: logging.Logger, heartbeat_interval_s: int = 5):
        self.logger = logger
        self.heartbeat_interval_s = heartbeat_interval_s
        self._last_heartbeat = 0.0
        self._start_ts = time.time()
        self._total_chunks = 0

    def _ts(self) -> str:
        return time.strftime("%H:%M:%S")

    def on_stage(self, stage: str, extras: Optional[Dict[str, Any]] = None) -> None:
        msg = f"[CLEANUP][{self._ts()}] {stage}"
        if extras:
            msg += " " + json.dumps(extras, ensure_ascii=False)
        self.logger.info(msg)

    def on_chunking_done(self, total_chunks: int) -> None:
        self._total_chunks = total_chunks
        self.logger.info(f"[CLEANUP][{self._ts()}] Chunking complete: {total_chunks} chunks")

    def on_chunk_start(self, idx: int, total: int) -> None:
        self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Start")

    def on_llm_submit(self, idx: int, total: int) -> None:
        self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Submitting to LLM…")

    def on_llm_wait_start(self, idx: int, total: int) -> None:
        self._last_heartbeat = 0.0
        self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Waiting for LLM response…")

    def on_llm_wait_heartbeat(self, idx: int, total: int, elapsed_s: int) -> None:
        now = time.time()
        if self._last_heartbeat == 0.0 or (now - self._last_heartbeat) >= self.heartbeat_interval_s:
            self._last_heartbeat = now
            self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Still waiting… {elapsed_s}s elapsed")

    def on_llm_wait_end(self, idx: int, total: int, latency_s: float) -> None:
        self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Response received in {latency_s:.1f}s")

    def on_chunk_result(self, idx: int, total: int, tokens_in: Optional[int], tokens_out: Optional[int], latency_s: float) -> None:
        tok_info = f"(tokens in {tokens_in}, out {tokens_out})" if (tokens_in is not None or tokens_out is not None) else ""
        self.logger.info(f"[CLEANUP][{self._ts()}] [Chunk {idx}/{total}] Cleaned {tok_info} in {latency_s:.1f}s")

    def on_retry(self, idx: int, attempt: int, max_attempts: int, backoff_s: int, error: str) -> None:
        self.logger.warning(f"[CLEANUP][{self._ts()}] [Chunk {idx}] LLM call failed: {error}. Retry {attempt}/{max_attempts} in {backoff_s}s")

    def on_error_giveup(self, idx: int, error: str) -> None:
        self.logger.warning(f"[CLEANUP][{self._ts()}] [Chunk {idx}] Failed after retries, using original text. Error: {error}")

    def on_summary(self, total: int, retries: int, tokens_in: Optional[int], tokens_out: Optional[int], elapsed_s: int) -> None:
        tok_info = f"tokens in ~{tokens_in or 0}, out ~{tokens_out or 0}"
        self.logger.info(f"[CLEANUP][{self._ts()}] Cleanup summary: {total} chunks, retries {retries}, {tok_info}, elapsed {elapsed_s//60:02d}:{elapsed_s%60:02d}")


class JsonFileProgressReporter(ProgressReporter):
    def __init__(self, status_file: Path):
        self.status_file = status_file
        # truncate/create file
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            self.status_file.write_text("", encoding="utf-8")
        except Exception:
            pass

    def _write(self, event: Dict[str, Any]) -> None:
        try:
            with self.status_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def on_stage(self, stage: str, extras: Optional[Dict[str, Any]] = None) -> None:
        ev = {"t": time.time(), "event": "stage", "stage": stage}
        if extras:
            ev.update(extras)
        self._write(ev)

    def on_chunking_done(self, total_chunks: int) -> None:
        self._write({"t": time.time(), "event": "chunking_done", "total": total_chunks})

    def on_chunk_start(self, idx: int, total: int) -> None:
        self._write({"t": time.time(), "event": "chunk_start", "idx": idx, "total": total})

    def on_llm_submit(self, idx: int, total: int) -> None:
        self._write({"t": time.time(), "event": "llm_submit", "idx": idx, "total": total})

    def on_llm_wait_start(self, idx: int, total: int) -> None:
        self._write({"t": time.time(), "event": "llm_wait_start", "idx": idx, "total": total})

    def on_llm_wait_heartbeat(self, idx: int, total: int, elapsed_s: int) -> None:
        self._write({"t": time.time(), "event": "llm_wait_heartbeat", "idx": idx, "total": total, "elapsed_s": elapsed_s})

    def on_llm_wait_end(self, idx: int, total: int, latency_s: float) -> None:
        self._write({"t": time.time(), "event": "llm_wait_end", "idx": idx, "total": total, "latency_s": latency_s})

    def on_chunk_result(self, idx: int, total: int, tokens_in: Optional[int], tokens_out: Optional[int], latency_s: float) -> None:
        self._write({"t": time.time(), "event": "chunk_result", "idx": idx, "total": total, "tokens_in": tokens_in, "tokens_out": tokens_out, "latency_s": latency_s})

    def on_retry(self, idx: int, attempt: int, max_attempts: int, backoff_s: int, error: str) -> None:
        self._write({"t": time.time(), "event": "retry", "idx": idx, "attempt": attempt, "max_attempts": max_attempts, "backoff_s": backoff_s, "error": error})

    def on_error_giveup(self, idx: int, error: str) -> None:
        self._write({"t": time.time(), "event": "giveup", "idx": idx, "error": error})

    def on_summary(self, total: int, retries: int, tokens_in: Optional[int], tokens_out: Optional[int], elapsed_s: int) -> None:
        self._write({"t": time.time(), "event": "summary", "total": total, "retries": retries, "tokens_in": tokens_in, "tokens_out": tokens_out, "elapsed_s": elapsed_s})


# -------- Pure helpers (no class state) --------

def analyze(text: str) -> Dict[str, int]:
    """Pure function: analyze text for common OCR artifacts."""
    return {
        'excessive_line_breaks': len(re.findall(r'\n\s*\n\s*\n', text)),
        'hyphenated_words': len(re.findall(r'\w+-\s*\n\s*\w+', text)),
        'single_line_paragraphs': len(re.findall(r'\n\s*\S[^\n]*\n\s*\n', text)),
        'page_numbers': len(re.findall(r'\n\s*\d+\s*\n', text)),
        'short_lines': len([line for line in text.split('\n') if 0 < len(line.strip()) < 30]),
    }


def create_cleanup_prompt() -> str:
    """Create the prompt for LLM-based OCR cleanup"""
    return """Te egy magyar nyelvű szöveg OCR hibáinak javítására specializálódott asszisztens vagy. 

FELADATOD:
1. Távolítsd el az OCR által okozott felesleges sortöréseket és oldalelválasztásokat
2. Egyesítsd a sorvégeken elválasztott magyar szavakat (pl. "szó-
tag" → "szótag")
3. Távolítsd el a felesleges szóközöket és formázási hibákat
4. Őrizd meg a bekezdések természetes szerkezetét
5. NE változtasd meg a szöveg jelentését vagy tartalmát

FONTOS SZABÁLYOK:
- Csak az OCR hibákat javítsd, a tartalmat ne módosítsd
- A magyar nyelvtan szabályait kövesd a szóegyesítésnél
- Őrizd meg a fejezetek és bekezdések logikus felépítését
- Ha bizonytalan vagy, inkább hagyd változatlanul

Kérlek, tisztítsd meg a következő szöveget:

"""


def chunk_text(text: str, max_tokens_per_chunk: int) -> List[str]:
    """Pure function: split text into chunks suitable for LLM processing.
    Rough estimation: 1 token ≈ 2 chars for conservative chunking here.
    """
    max_chars = max_tokens_per_chunk * 2

    chunks: List[str] = []
    current_chunk = ""

    # Split by paragraphs first
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_chunk) + len(paragraph) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                # Paragraph is too long, split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_chars:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            # Even single sentence is too long, force split
                            chunks.append(sentence[:max_chars])
                            current_chunk = sentence[max_chars:]
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def clean_chunks(
    chunks: List[str],
    client: openai.AzureOpenAI,
    deployment: str,
    temperature: float,
    max_tokens_response: int,
    debug_mode: bool = False,
    debug_dir: Optional[Path] = None,
    reporter: Optional[ProgressReporter] = None,
) -> List[str]:
    """Helper handling retries, progress, and debug artifacts writing."""
    cleaned_chunks: List[str] = []
    total = len(chunks)
    if reporter:
        reporter.on_stage("Preparing content")
        reporter.on_chunking_done(total)

    logger.info(f"Processing {total} text chunks...")
    max_retries = 3
    retry_delay = 2
    total_tokens_in = 0
    total_tokens_out = 0
    total_retries = 0
    start_ts = time.time()

    for i, chunk in enumerate(chunks, start=1):
        if reporter:
            reporter.on_chunk_start(i, total)
            reporter.on_llm_submit(i, total)

        last_error: Optional[str] = None
        t0 = time.time()
        for attempt in range(max_retries):
            if attempt > 0:
                total_retries += 1
            try:
                messages = [
                    {"role": "system", "content": create_cleanup_prompt()},
                    {"role": "user", "content": chunk},
                ]

                wait_start = time.time()
                if reporter:
                    reporter.on_llm_wait_start(i, total)

                # We cannot truly stream Azure responses with this SDK call; emulate heartbeat while waiting
                # by polling elapsed time around the synchronous call.
                # Start the request
                response = client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens_response,
                )
                # LLM returned; report end
                latency = time.time() - wait_start
                if reporter:
                    reporter.on_llm_wait_end(i, total, latency)

                cleaned_text = response.choices[0].message.content.strip()
                cleaned_chunks.append(cleaned_text)

                # Token accounting if available
                tokens_in = None
                tokens_out = None
                try:
                    usage = getattr(response, "usage", None)
                    if usage:
                        tokens_in = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
                        tokens_out = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
                        if isinstance(tokens_in, int):
                            total_tokens_in += tokens_in
                        if isinstance(tokens_out, int):
                            total_tokens_out += tokens_out
                except Exception:
                    pass

                if reporter:
                    reporter.on_chunk_result(i, total, tokens_in, tokens_out, latency)

                if debug_mode and debug_dir:
                    llm_debug_dir = debug_dir / "llm_requests_responses"
                    llm_debug_dir.mkdir(parents=True, exist_ok=True)
                    request_file = llm_debug_dir / f"llm_chunk_{i}_request_attempt_{attempt+1}.json"
                    response_file = llm_debug_dir / f"llm_chunk_{i}_response_attempt_{attempt+1}.json"
                    with open(request_file, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens_response,
                            },
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )
                    with open(response_file, "w", encoding="utf-8") as f:
                        try:
                            f.write(response.model_dump_json(indent=2))
                        except Exception:
                            # Fallback serialization
                            f.write(json.dumps(response.__dict__, default=str, indent=2))
                    logger.debug(f"LLM request/response for chunk {i} saved to {llm_debug_dir}")
                break
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    if reporter:
                        reporter.on_retry(i, attempt + 1, max_retries, retry_delay, last_error)
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"Failed to process chunk {i}, using original text: {last_error}")
                    if reporter:
                        reporter.on_error_giveup(i, last_error or "unknown error")
                    cleaned_chunks.append(chunk)

        # Heartbeat while waiting was handled around the call; for very long waits, we log periodic messages
        # Note: since the call is synchronous, we emulate heartbeats by printing periodic 'Still waiting' logs
        # in on_llm_wait_heartbeat from the call site above (not feasible without threads). Kept simple.

    elapsed = int(time.time() - start_ts)
    if reporter:
        reporter.on_summary(total, total_retries, total_tokens_in or None, total_tokens_out or None, elapsed)
    return cleaned_chunks


def reconstruct_html(cleaned_text: str, original_html: str) -> str:
    """Pure function: reconstruct HTML structure with cleaned text."""
    if not cleaned_text.strip():
        return """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Empty Chapter</title></head>
<body><p>This chapter appears to be empty.</p></body>
</html>"""

    paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [cleaned_text.strip()]

    html_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter</title></head>
<body>
"""
    for paragraph in paragraphs:
        if paragraph.strip():
            if len(paragraph) < 100 and not paragraph.endswith("."):
                html_content += f"<h2>{paragraph}</h2>\n"
            else:
                html_content += f"<p>{paragraph}</p>\n"

    html_content += """</body>
</html>"""
    return html_content


# -------- Single, consolidated class (do not redefine below) --------

class EPUBOCRCleaner:
    """Cleans OCR artifacts from EPUB files using Azure GPT-4.1.

    Note: Do not redefine this class later in this module. Keep helper functions pure above.
    """

    # Keep backward-compatible signature: accept arbitrary *args/**kwargs and map them.
    def __init__(self, *args, **kwargs):
        # Support both legacy signature (debug_mode=False, debug_dir=None) and new kwargs
        debug_mode = False
        debug_dir: Optional[Path] = None

        # Map positional args if present
        if len(args) > 0:
            debug_mode = bool(args[0])
        if len(args) > 1:
            debug_dir = args[1]

        # Map keyword args
        debug_mode = kwargs.pop("debug_mode", debug_mode)
        debug_dir = kwargs.pop("debug_dir", debug_dir)
        azure_openai_cfg: Optional[AzureOpenAIConfig] = kwargs.pop("azure_openai_cfg", None)
        client_factory: Optional[Callable[[AzureOpenAIConfig], openai.AzureOpenAI]] = kwargs.pop("client_factory", None)
        runtime_cfg: Optional[CleanerRuntimeConfig] = kwargs.pop("runtime_cfg", None)
        status_file: Optional[Path] = kwargs.pop("status_file", None)

        # Ignore any unexpected kwargs for backward compatibility

        self.debug_mode = debug_mode
        self.debug_dir = debug_dir
        self.status_file = status_file

        # Prefer injected typed config. Fall back to env for backward-compat if not provided.
        if azure_openai_cfg is None:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            if not all([endpoint, api_key, api_version, deployment]):
                raise LLMError("Missing Azure OpenAI configuration. Provide AzureOpenAIConfig or set environment variables.")
            self.azure_cfg = AzureOpenAIConfig(
                endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
                deployment=deployment,
            )
        else:
            self.azure_cfg = azure_openai_cfg

        # Runtime tuning config
        self.runtime_cfg = runtime_cfg or CleanerRuntimeConfig()

        # Initialize client
        if client_factory:
            self.client = client_factory(self.azure_cfg)
        else:
            self.client = openai.AzureOpenAI(
                api_key=self.azure_cfg.api_key,
                api_version=self.azure_cfg.api_version,
                azure_endpoint=self.azure_cfg.endpoint,
            )

        # Initialize reporters
        self.console_reporter = ConsoleProgressReporter(logger)
        self.json_reporter: Optional[JsonFileProgressReporter] = None
        if self.status_file:
            try:
                self.json_reporter = JsonFileProgressReporter(Path(self.status_file))
            except Exception:
                self.json_reporter = None

    # ----- Instance wrappers around pure helpers -----

    def analyze_ocr_artifacts(self, text: str) -> Dict[str, int]:
        """Back-compat wrapper calling pure analyze()."""
        return analyze(text)

    def chunk_text(self, text: str) -> List[str]:
        """Instance wrapper that uses runtime_cfg for max_tokens_per_chunk."""
        return chunk_text(text, self.runtime_cfg.max_tokens_per_chunk)

    def clean_text_with_llm(self, text: str) -> str:
        """Clean text using Azure GPT-4.1 (uses pure helpers)."""
        chunks = self.chunk_text(text)
        # Combine reporters
        reporter: Optional[ProgressReporter] = self.console_reporter
        if self.json_reporter:
            # simple composite behavior: call both by wrapping
            class CompositeReporter(ProgressReporter):
                def __init__(self, a: ProgressReporter, b: ProgressReporter) -> None:
                    self.a = a; self.b = b
                def on_stage(self, s, e=None): self.a.on_stage(s, e); self.b.on_stage(s, e)
                def on_chunking_done(self, t): self.a.on_chunking_done(t); self.b.on_chunking_done(t)
                def on_chunk_start(self, i, t): self.a.on_chunk_start(i, t); self.b.on_chunk_start(i, t)
                def on_llm_submit(self, i, t): self.a.on_llm_submit(i, t); self.b.on_llm_submit(i, t)
                def on_llm_wait_start(self, i, t): self.a.on_llm_wait_start(i, t); self.b.on_llm_wait_start(i, t)
                def on_llm_wait_heartbeat(self, i, t, e): self.a.on_llm_wait_heartbeat(i, t, e); self.b.on_llm_wait_heartbeat(i, t, e)
                def on_llm_wait_end(self, i, t, l): self.a.on_llm_wait_end(i, t, l); self.b.on_llm_wait_end(i, t, l)
                def on_chunk_result(self, i, t, ti, to, l): self.a.on_chunk_result(i, t, ti, to, l); self.b.on_chunk_result(i, t, ti, to, l)
                def on_retry(self, i, a, m, b, e): self.a.on_retry(i, a, m, b, e); self.b.on_retry(i, a, m, b, e)
                def on_error_giveup(self, i, e): self.a.on_error_giveup(i, e); self.b.on_error_giveup(i, e)
                def on_summary(self, t, r, ti, to, e): self.a.on_summary(t, r, ti, to, e); self.b.on_summary(t, r, ti, to, e)
            reporter = CompositeReporter(self.console_reporter, self.json_reporter)

        cleaned_chunks = clean_chunks(
            chunks=chunks,
            client=self.client,
            deployment=self.azure_cfg.deployment or "",
            temperature=self.runtime_cfg.temperature,
            max_tokens_response=self.runtime_cfg.max_tokens_response,
            debug_mode=self.debug_mode,
            debug_dir=self.debug_dir,
            reporter=reporter,
        )
        return "\n\n".join(cleaned_chunks)

    def reconstruct_html(self, cleaned_text: str, original_html: str) -> str:
        """Instance wrapper calling pure reconstruct_html()."""
        return reconstruct_html(cleaned_text, original_html)

    # ----- File/EPUB operations -----

    def extract_epub_content(self, epub_path: str) -> Tuple[Dict, str]:
        """Extract content from EPUB file"""
        logger.info(f"Extracting EPUB content from: {epub_path}")

        # Create temporary directory for extraction
        if self.debug_mode and self.debug_dir:
            extract_base_dir = self.debug_dir / "epub_extracted_content"
            extract_base_dir.mkdir(parents=True, exist_ok=True)
            temp_dir = tempfile.mkdtemp(dir=extract_base_dir)
            logger.debug(f"EPUB content extracted to: {temp_dir}")
        else:
            temp_dir = tempfile.mkdtemp()

        try:
            # Extract EPUB (which is a ZIP file)
            with zipfile.ZipFile(epub_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Read the EPUB using ebooklib
            book = epub.read_epub(epub_path)

            # Extract text content from all items
            content_items = []
            for item in book.get_items():
                if item.get_type() == 9:  # EBOOKLIB_ITEM_DOCUMENT
                    soup = BeautifulSoup(item.get_content(), 'lxml')
                    text_content = soup.get_text()

                    content_items.append({
                        'id': item.get_id(),
                        'file_name': item.get_name(),
                        'title': getattr(item, 'title', ''),
                        'content': text_content,
                        'html_content': item.get_content().decode('utf-8')
                    })

            metadata = {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
                'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown',
                'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'hu',
                'identifier': book.get_metadata('DC', 'identifier')[0][0] if book.get_metadata('DC', 'identifier') else 'unknown'
            }

            return {'content_items': content_items, 'metadata': metadata}, temp_dir

        except Exception as e:
            # Only remove temp_dir if not in debug mode, otherwise leave for inspection
            if not (self.debug_mode and self.debug_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise EPUBError(f"Error extracting EPUB: {str(e)}")

    def create_cleaned_epub(self, original_data: Dict, cleaned_content: List[Dict], output_path: str, debug: bool = False):
        """Create a new EPUB with cleaned content"""
        logger.info("Creating cleaned EPUB...")

        # Check if we have any content to work with
        if not cleaned_content:
            raise EPUBError("No content found to create EPUB. All chapters appear to be empty.")

        if debug:
            logger.debug(f"Starting EPUB creation with {len(cleaned_content)} chapters")

        # Create new book
        book = epub.EpubBook()

        # Set metadata
        metadata = original_data['metadata']
        book.set_identifier(metadata['identifier'])
        book.set_title(f"{metadata['title']} (Cleaned)")
        book.set_language(metadata['language'])
        book.add_author(metadata['author'])

        if debug:
            logger.debug(f"Set metadata - Title: {metadata['title']}, Language: {metadata['language']}")

        # Add cleaned content items
        chapters = []
        for i, item_data in enumerate(cleaned_content):
            if debug:
                logger.debug(f"Processing chapter {i+1}: {item_data['file_name']}")

            html_content = item_data.get('cleaned_html', '')
            if not html_content.strip():
                if debug:
                    logger.debug(f"Empty HTML content for {item_data['file_name']}, creating placeholder")
                html_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Empty Chapter</title></head>
<body><p>This chapter appears to be empty.</p></body>
</html>"""

            if debug:
                logger.debug(f"HTML content length: {len(html_content)} chars")
                logger.debug(f"HTML content sample: {repr(html_content[:150])}")

            # Create chapter
            chapter = epub.EpubHtml(
                title=item_data.get('title', f'Chapter {i+1}'),
                file_name=item_data['file_name'],
                lang=metadata['language']
            )

            try:
                if isinstance(html_content, str):
                    chapter.content = html_content.encode('utf-8')
                else:
                    chapter.content = html_content

                if debug:
                    print(f"🔍 DEBUG: Set content for {item_data['file_name']} - Content type: {type(chapter.content)}, Length: {len(chapter.content)}")

            except Exception as e:
                logger.error(f"Error setting content for {item_data['file_name']}: {str(e)}")
                if debug:
                    logger.debug("Falling back to simple string assignment")
                chapter.content = html_content

            book.add_item(chapter)
            chapters.append(chapter)

        # Ensure at least one chapter
        if not chapters:
            if debug:
                logger.debug("No chapters found, creating placeholder")
            placeholder_chapter = epub.EpubHtml(
                title='Placeholder Chapter',
                file_name='placeholder.xhtml',
                lang=metadata['language']
            )
            placeholder_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Placeholder</title></head>
<body><p>This EPUB was processed but no readable content was found.</p></body>
</html>"""
            placeholder_chapter.content = placeholder_content.encode('utf-8')
            book.add_item(placeholder_chapter)
            chapters.append(placeholder_chapter)

        if debug:
            print(f"🔍 DEBUG: Total chapters to include: {len(chapters)}")

        # Define table of contents and spine
        book.toc = chapters
        book.spine = ['nav'] + chapters

        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        if debug:
            logger.debug("Added navigation files, about to write EPUB")

        # Write the EPUB
        try:
            epub.write_epub(output_path, book, {})
            logger.info(f"Cleaned EPUB saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error writing EPUB: {str(e)}")
            raise EPUBError(str(e))

    def clean_epub(self, input_path: str, output_path: str = None, debug: bool = False, save_interim: bool = False):
        """Main method to clean an EPUB file"""
        if not output_path:
            base_name = Path(input_path).stem
            output_path = f"{base_name}_cleaned.epub"

        logger.info(f"Starting EPUB cleanup: {input_path}")
        logger.info(f"Output will be saved to: {output_path}")

        # Create backup
        backup_path = f"{input_path}.backup"
        if not os.path.exists(backup_path):
            shutil.copy2(input_path, backup_path)
            logger.info(f"Backup created: {backup_path}")

        # Create interim directory if saving to disk
        interim_dir = None
        if save_interim:
            if self.debug_mode and self.debug_dir:
                interim_base_dir = self.debug_dir / "interim_json_results"
                interim_base_dir.mkdir(parents=True, exist_ok=True)
                interim_dir = tempfile.mkdtemp(dir=interim_base_dir)
                logger.debug(f"Interim JSON results will be saved to: {interim_dir}")
            else:
                interim_dir = tempfile.mkdtemp(prefix="epub_cleanup_")
                logger.info(f"Interim results will be saved to: {interim_dir}")

        try:
            # Extract content
            original_data, temp_dir = self.extract_epub_content(input_path)

            if debug:
                logger.debug(f"Found {len(original_data['content_items'])} content items")
                for i, item in enumerate(original_data['content_items']):
                    logger.debug(f"  Item {i+1}: {item['file_name']} - Content length: {len(item['content'])} chars")
                try:
                    import psutil  # Optional monitoring
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    logger.debug(f"Current memory usage: {memory_mb:.1f} MB")
                except Exception:
                    pass

            # Process each content item
            cleaned_content = []
            total_artifacts = 0

            for item in original_data['content_items']:
                # Skip navigation files and other special files
                if item['file_name'] in ['nav.xhtml', 'toc.ncx', 'content.opf'] or 'nav' in item['file_name'].lower():
                    if debug:
                        logger.debug(f"Skipping navigation file: {item['file_name']}")
                    continue

                if item['content'].strip():  # Only process items with content
                    logger.info(f"Processing: {item['file_name']}")

                    # Analyze artifacts
                    artifacts = self.analyze_ocr_artifacts(item['content'])
                    total_artifacts += sum(artifacts.values())
                    logger.info(f"Found artifacts: {artifacts}")

                    if debug:
                        logger.debug(f"Original content preview (first 200 chars): {repr(item['content'][:200])}")

                    # Clean text with LLM
                    cleaned_text = self.clean_text_with_llm(item['content'])

                    if debug:
                        logger.debug(f"Cleaned text preview (first 200 chars): {repr(cleaned_text[:200])}")

                    # Reconstruct HTML
                    cleaned_html = self.reconstruct_html(cleaned_text, item['html_content'])

                    if debug:
                        logger.debug(f"HTML content preview (first 300 chars): {repr(cleaned_html[:300])}")

                    # Save interim results to disk if requested
                    if save_interim and interim_dir:
                        interim_file = os.path.join(interim_dir, f"{item['file_name']}.json")
                        interim_data = {
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'original_content': item['content'],
                            'cleaned_text': cleaned_text,
                            'cleaned_html': cleaned_html,
                            'artifacts': artifacts
                        }
                        with open(interim_file, 'w', encoding='utf-8') as f:
                            json.dump(interim_data, f, ensure_ascii=False, indent=2)

                        if debug:
                            logger.debug(f"Saved interim results to: {interim_file}")

                        cleaned_content.append({
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'cleaned_html': cleaned_html
                        })
                    else:
                        cleaned_content.append({
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'cleaned_html': cleaned_html
                        })
                else:
                    if debug:
                        logger.debug(f"Skipping empty item: {item['file_name']}")

            if debug:
                logger.debug(f"Final cleaned_content has {len(cleaned_content)} items")
                for i, item in enumerate(cleaned_content):
                    logger.debug(f"  Item {i+1}: {item['file_name']} - HTML length: {len(item['cleaned_html'])} chars")

            # Create new EPUB
            self.create_cleaned_epub(original_data, cleaned_content, output_path, debug=debug)

            # Cleanup temporary extraction directory if not in debug mode
            if not (self.debug_mode and self.debug_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            # Cleanup interim JSON directory if not in debug mode
            if save_interim and interim_dir and not (self.debug_mode and self.debug_dir):
                shutil.rmtree(interim_dir, ignore_errors=True)

            logger.info("EPUB cleanup completed!")
            logger.info(f"Original file: {input_path}")
            logger.info(f"Cleaned file: {output_path}")
            logger.info(f"Backup file: {backup_path}")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise EPUBError(str(e))
