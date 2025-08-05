import logging
from pathlib import Path
from typing import Optional, Tuple
import json, time

from scan2epub.ocr.azure_cu import PDFOCRProcessor
from scan2epub.epub.builder import EPUBBuilder
from scan2epub.azure.storage import AzureStorageHandler
from scan2epub.utils.errors import OCRError, EPUBError
from scan2epub.config import AppConfig  # typed config


def run_ocr_to_epub(
    cfg: AppConfig,
    input_path: str,
    output_epub: str,
    language: str = "hu",
    debug: bool = False,
    debug_dir: Optional[Path] = None,
    status_file: Optional[Path] = None,
) -> Tuple[str, Optional[str]]:
    """
    Run OCR on a PDF (local file or URL) and create an EPUB with raw OCR text.
    Returns (output_epub_path, interim_debug_file_or_None)
    """
    logger = logging.getLogger("scan2epub.pipeline")
    storage_handler: Optional[AzureStorageHandler] = None
    interim_file: Optional[str] = None

    def _status(event: str, **extras):
        if not status_file:
            return
        try:
            status_file.parent.mkdir(parents=True, exist_ok=True)
            with status_file.open("a", encoding="utf-8") as f:
                payload = {"t": time.time(), "event": "pipeline_stage", "stage": event}
                if extras:
                    payload.update(extras)
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    try:
        _status("ocr_start", input=input_path, output=str(output_epub))
        # Determine if input is URL or local file
        pdf_url = input_path
        if not input_path.startswith(("http://", "https://")):
            # Local file - upload using Azure Storage via typed config
            storage_handler = AzureStorageHandler(
                storage_cfg=cfg.azure_storage,
                debug_mode=debug,
                debug_dir=debug_dir,
            )
            _status("upload_start", local_path=input_path)
            pdf_url = storage_handler.upload_pdf(input_path)
            _status("upload_done", url=pdf_url)

        # OCR
        pdf_processor = PDFOCRProcessor(debug_mode=debug, debug_dir=debug_dir)
        _status("content_understanding_submit", url=pdf_url)
        ocr_result = pdf_processor.process_pdf(pdf_url)
        _status("content_understanding_result_received")
        extracted_text = pdf_processor.extract_text_from_ocr_result(ocr_result)
        _status("ocr_text_extracted", approx_len=len(extracted_text))

        # Build EPUB
        title = Path(input_path).stem
        author = "Unknown"
        epub_builder = EPUBBuilder()
        epub_builder.set_metadata(title=title, author=author, language=language)
        epub_builder.add_chapter(title="Document Content", content=extracted_text)
        _status("build_epub_raw_start")
        epub_builder.build_epub(output_epub)
        _status("build_epub_raw_done", path=str(output_epub))

        return output_epub, interim_file
    finally:
        # Cleanup uploaded blobs unless debug
        if storage_handler and cfg.processing.cleanup_on_failure and not debug:
            try:
                storage_handler.cleanup_all()
                _status("upload_cleanup_done")
            except Exception:
                pass


def run_cleanup(
    cfg: AppConfig,
    input_epub: str,
    output_epub: str,
    debug: bool = False,
    save_interim: bool = False,
    debug_dir: Optional[Path] = None,
    status_file: Optional[Path] = None,
) -> str:
    """
    Clean an EPUB (OCR artifacts) with Azure OpenAI and write a cleaned EPUB.
    Returns output_epub_path.
    """
    # Import here to avoid circular import and to keep dependency localized
    from scan2epub.epub.cleaner import EPUBOCRCleaner  # type: ignore

    # Pass typed Azure OpenAI config into the cleaner (falls back to env if None)
    cleaner = EPUBOCRCleaner(
        debug_mode=debug,
        debug_dir=debug_dir,
        azure_openai_cfg=cfg.azure_openai,
        status_file=status_file,
    )
    cleaner.clean_epub(input_epub, output_epub, debug=debug, save_interim=save_interim)
    return output_epub


def run_full_pipeline(
    cfg: AppConfig,
    input_pdf: str,
    output_epub: str,
    language: str = "hu",
    debug: bool = False,
    save_interim: bool = False,
    debug_dir: Optional[Path] = None,
    status_file: Optional[Path] = None,
) -> str:
    """
    Full pipeline: PDF -> OCR -> interim EPUB -> cleanup -> final EPUB.
    Returns final output_epub_path.
    """
    # Step 1: OCR to interim EPUB
    output_path_obj = Path(output_epub)
    interim_epub_path = output_path_obj.with_stem(output_path_obj.stem + "_interim_ocr").with_suffix(".epub")

    # Pipeline-level status helper
    def _status(event: str, **extras):
        if not status_file:
            return
        try:
            status_file.parent.mkdir(parents=True, exist_ok=True)
            with status_file.open("a", encoding="utf-8") as f:
                payload = {"t": time.time(), "event": "pipeline_stage", "stage": event}
                if extras:
                    payload.update(extras)
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    _status("pipeline_start", input=input_pdf, output=output_epub)
    run_ocr_to_epub(
        cfg=cfg,
        input_path=input_pdf,
        output_epub=str(interim_epub_path),
        language=language,
        debug=debug,
        debug_dir=debug_dir,
        status_file=status_file,
    )
    _status("ocr_done", interim=str(interim_epub_path))

    # Step 2: Cleanup interim EPUB to final
    _status("cleanup_start")
    final_path = run_cleanup(
        cfg=cfg,
        input_epub=str(interim_epub_path),
        output_epub=output_epub,
        debug=debug,
        save_interim=save_interim,
        debug_dir=debug_dir,
        status_file=status_file,
    )
    _status("cleanup_done", final=output_epub)

    # Move or remove interim
    if debug and debug_dir:
        # Keep interim in debug dir
        target = debug_dir / Path(interim_epub_path).name
        try:
            Path(interim_epub_path).replace(target)
            logging.getLogger("scan2epub.pipeline").info(f"Moved interim file to debug directory: {target}")
        except Exception:
            pass
    else:
        try:
            Path(interim_epub_path).unlink(missing_ok=True)
            logging.getLogger("scan2epub.pipeline").info(f"Cleaned up interim file: {interim_epub_path}")
        except Exception:
            pass

    _status("pipeline_done", result=final_path)
    return final_path
