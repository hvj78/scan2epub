import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from ebooklib import epub

from scan2epub.translate.translator import ITranslator
from scan2epub.utils.errors import EPUBError, TranslationError
# Reuse the same HTML reconstruction heuristic used by the cleaner to keep consistency
from scan2epub.epub.cleaner import reconstruct_html

logger = logging.getLogger("scan2epub.epub.translator")


@dataclass
class TranslatorRuntimeConfig:
    """
    Runtime tuning for translation batching and behavior.
    Keep small and conservative to avoid provider limits.
    """
    max_paragraphs_per_batch: int = 100
    max_chars_per_batch: int = 30000  # keep conservative headroom
    title_suffix_template: str = " (Translated to {lang})"


class EPUBTranslator:
    """
    Translates the readable content of an EPUB file using a provided translator implementation.
    """
    def __init__(
        self,
        translator: ITranslator,
        debug_mode: bool = False,
        debug_dir: Optional[Path] = None,
        status_file: Optional[Path] = None,
        allow_noop: bool = False,
        min_changed_ratio: float = 0.0,
        runtime_cfg: Optional[TranslatorRuntimeConfig] = None,
    ) -> None:
        self.translator = translator
        self.debug_mode = debug_mode
        self.debug_dir = debug_dir
        self.status_file = Path(status_file) if status_file else None
        self.allow_noop = allow_noop
        self.min_changed_ratio = min_changed_ratio
        self.runtime_cfg = runtime_cfg or TranslatorRuntimeConfig()

        if self.debug_mode and self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

    # ------- Status helper -------

    def _status(self, event: str, **extras: Any) -> None:
        if not self.status_file:
            return
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with self.status_file.open("a", encoding="utf-8") as f:
                payload = {"t": time.time(), "event": "translate", "stage": event}
                if extras:
                    payload.update(extras)
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ------- EPUB helpers (adapted from cleaner) -------

    def extract_epub_content(self, epub_path: str) -> Tuple[Dict[str, Any], str]:
        """Extract content from EPUB file (parallel to cleaner.extract_epub_content)."""
        logger.info(f"Extracting EPUB content from: {epub_path}")

        # Create temporary directory for extraction
        if self.debug_mode and self.debug_dir:
            extract_base_dir = self.debug_dir / "epub_extracted_content_for_translation"
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
                    soup = BeautifulSoup(item.get_content(), 'lxml-xml')
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
            raise EPUBError(f"Error extracting EPUB for translation: {str(e)}")

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs using blank-line separation, fallback to line grouping if needed.
        """
        if not text:
            return []
        # Primary split by double newlines
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        if parts:
            return parts
        # Fallback: split by single newlines and group short lines
        lines = [ln.strip() for ln in text.split("\n")]
        acc: List[str] = []
        buf: List[str] = []
        cur_len = 0
        for ln in lines:
            if not ln:
                if buf:
                    acc.append(" ".join(buf).strip())
                    buf = []
                    cur_len = 0
                continue
            if cur_len + len(ln) > 2000:  # simple grouping threshold
                if buf:
                    acc.append(" ".join(buf).strip())
                    buf = []
                    cur_len = 0
            buf.append(ln)
            cur_len += len(ln) + 1
        if buf:
            acc.append(" ".join(buf).strip())
        return [p for p in acc if p]

    def _batch_paragraphs(self, paragraphs: List[str]) -> List[List[str]]:
        """
        Batch paragraphs into lists respecting runtime_cfg limits.
        """
        batches: List[List[str]] = []
        cur: List[str] = []
        cur_chars = 0
        for p in paragraphs:
            p_len = len(p)
            if cur and (
                len(cur) + 1 > self.runtime_cfg.max_paragraphs_per_batch
                or cur_chars + p_len > self.runtime_cfg.max_chars_per_batch
            ):
                batches.append(cur)
                cur = [p]
                cur_chars = p_len
            else:
                cur.append(p)
                cur_chars += p_len
        if cur:
            batches.append(cur)
        return batches

    def _translate_paragraphs(
        self,
        paragraphs: List[str],
        to_lang: str,
        from_lang: Optional[str],
        llm_debug_dir: Optional[Path],
    ) -> List[str]:
        """
        Translate paragraphs using the provided translator; writes debug artifacts when enabled.
        """
        if not paragraphs:
            return []
        translated: List[str] = []
        batches = self._batch_paragraphs(paragraphs)
        total = len(batches)
        self._status("translate_item_chunking_done", batches=total, paragraphs=len(paragraphs))
        for i, batch in enumerate(batches, start=1):
            self._status("translate_batch_start", idx=i, total=total, batch_size=len(batch))
            # Debug: save request
            if self.debug_mode and llm_debug_dir:
                try:
                    llm_debug_dir.mkdir(parents=True, exist_ok=True)
                    (llm_debug_dir / f"translator_batch_{i}_request.json").write_text(
                        json.dumps({"to": to_lang, "from": from_lang, "segments": batch}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass

            t0 = time.time()
            out = self.translator.translate_text(batch, to_lang=to_lang, from_lang=from_lang)
            latency = time.time() - t0
            translated.extend(out)
            self._status("translate_batch_done", idx=i, total=total, latency_s=round(latency, 3))

            # Debug: save response
            if self.debug_mode and llm_debug_dir:
                try:
                    (llm_debug_dir / f"translator_batch_{i}_response.json").write_text(
                        json.dumps({"translated": out}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
        return translated

    def _create_translated_epub(
        self,
        original_data: Dict[str, Any],
        translated_content: List[Dict[str, str]],
        output_path: str,
        target_lang: str,
        debug: bool = False,
    ) -> None:
        """Create a new EPUB from translated HTML content (based on cleaner's create_cleaned_epub)."""
        logger.info("Creating translated EPUB...")

        if not translated_content:
            raise EPUBError("No content found to create translated EPUB. All chapters appear to be empty.")

        if debug:
            logger.debug(f"Starting EPUB creation with {len(translated_content)} chapters")

        # Create new book
        book = epub.EpubBook()

        # Set metadata (update language and title suffix)
        metadata = original_data['metadata']
        book.set_identifier(metadata['identifier'])
        new_title = f"{metadata['title']}{self.runtime_cfg.title_suffix_template.format(lang=target_lang)}"
        book.set_title(new_title)
        book.set_language(target_lang)
        book.add_author(metadata['author'])

        if debug:
            logger.debug(f"Set metadata - Title: {new_title}, Language: {target_lang}")

        # Add translated content items
        chapters = []
        for i, item_data in enumerate(translated_content):
            if debug:
                logger.debug(f"Processing chapter {i+1}: {item_data['file_name']}")

            html_content = item_data.get('translated_html', '')
            if not html_content.strip():
                if debug:
                    logger.debug(f"Empty HTML content for {item_data['file_name']}, creating placeholder")
                html_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Empty Chapter</title></head>
<body><p>This chapter appears to be empty after translation.</p></body>
</html>"""

            # Create chapter
            chapter = epub.EpubHtml(
                title=item_data.get('title', f'Chapter {i+1}'),
                file_name=item_data['file_name'],
                lang=target_lang
            )

            try:
                if isinstance(html_content, str):
                    chapter.content = html_content.encode('utf-8')
                else:
                    chapter.content = html_content
            except Exception as e:
                logger.error(f"Error setting content for {item_data['file_name']}: {str(e)}")
                chapter.content = html_content

            book.add_item(chapter)
            chapters.append(chapter)

        if not chapters:
            placeholder_chapter = epub.EpubHtml(
                title='Placeholder Chapter',
                file_name='placeholder.xhtml',
                lang=target_lang
            )
            placeholder_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Placeholder</title></head>
<body><p>This EPUB was processed but no readable content was found after translation.</p></body>
</html>"""
            placeholder_chapter.content = placeholder_content.encode('utf-8')
            book.add_item(placeholder_chapter)
            chapters.append(placeholder_chapter)

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
            logger.info(f"Translated EPUB saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error writing translated EPUB: {str(e)}")
            raise EPUBError(str(e))

    # ------- Main API -------

    def translate_epub(
        self,
        input_epub: str,
        output_epub: str,
        to_lang: str,
        from_lang: Optional[str] = None,
        debug: bool = False,
    ) -> str:
        """
        Translate EPUB file content and write to a new EPUB with updated language metadata.
        """
        self._status("translate_start", input=input_epub, output=output_epub, to_lang=to_lang)
        logger.info(f"Starting EPUB translation: {input_epub} -> {output_epub} (to: {to_lang})")

        # Extract content
        original_data, temp_dir = self.extract_epub_content(input_epub)

        try:
            if debug:
                logger.debug(f"Found {len(original_data['content_items'])} content items for translation")

            translated_content: List[Dict[str, str]] = []
            llm_debug_dir: Optional[Path] = None
            if self.debug_mode and self.debug_dir:
                llm_debug_dir = self.debug_dir / "translation_requests_responses"

            total_items = 0
            total_paragraphs = 0
            changed_paragraphs = 0

            for item in original_data['content_items']:
                # Skip navigation files and other special files
                if item['file_name'] in ['nav.xhtml', 'toc.ncx', 'content.opf'] or 'nav' in item['file_name'].lower():
                    if debug:
                        logger.debug(f"Skipping navigation file: {item['file_name']}")
                    continue

                text = item.get('content', '') or ''
                if not text.strip():
                    if debug:
                        logger.debug(f"Skipping empty item: {item['file_name']}")
                    continue

                total_items += 1
                paragraphs = self._split_paragraphs(text)
                total_paragraphs += len(paragraphs)
                self._status("translate_item_start", file=item['file_name'], paragraphs=len(paragraphs))

                translated_paragraphs = self._translate_paragraphs(paragraphs, to_lang, from_lang, llm_debug_dir)
                # Track changes for quality guardrails
                try:
                    diffs = sum(1 for a, b in zip(paragraphs, translated_paragraphs) if (a or "").strip() != (b or "").strip())
                except Exception:
                    diffs = 0
                changed_paragraphs += diffs

                # Join paragraphs back to a single string with blank lines
                translated_text = "\n\n".join(translated_paragraphs)

                # Reconstruct HTML (consistent with cleaner)
                translated_html = reconstruct_html(translated_text, item['html_content'])

                translated_content.append({
                    'file_name': item['file_name'],
                    'title': item['title'],
                    'translated_html': translated_html
                })

                self._status("translate_item_done", file=item['file_name'])

            if debug:
                logger.debug(f"Translation produced {len(translated_content)} content items")

            # Evaluate no-op / minimal-change guard before writing output
            ratio = (changed_paragraphs / max(1, total_paragraphs)) if total_paragraphs else 0.0
            if (not self.allow_noop) and (ratio <= self.min_changed_ratio):
                msg = f"No-op translation detected (changed {changed_paragraphs}/{total_paragraphs} paragraphs; ratio {ratio:.3f} <= {self.min_changed_ratio:.3f}). Aborting."
                logger.error(msg)
                self._status("translate_noop", total_paragraphs=total_paragraphs, changed_paragraphs=changed_paragraphs, ratio=round(ratio, 3))
                raise TranslationError(msg)

            # Create translated EPUB
            self._create_translated_epub(
                original_data=original_data,
                translated_content=translated_content,
                output_path=output_epub,
                target_lang=to_lang,
                debug=debug
            )

            logger.info("EPUB translation completed!")
            logger.info(f"Original file: {input_epub}")
            logger.info(f"Translated file: {output_epub}")

            self._status("translate_done", items=total_items, paragraphs=total_paragraphs, result=output_epub)
            return output_epub

        except Exception as e:
            logger.error(f"Error during translation: {str(e)}")
            self._status("translate_error", error=str(e))
            raise
        finally:
            # Cleanup temporary extraction directory if not in debug mode
            if not (self.debug_mode and self.debug_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
