import argparse
import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from scan2epub.config import AppConfig
from scan2epub.pipeline import run_ocr_to_epub, run_cleanup, run_full_pipeline, run_translate
from scan2epub.azure.preflight import PreflightChecker
from scan2epub.azure.diagnostics import AzureConfigTester
from scan2epub.utils.io import get_unique_debug_dir
from scan2epub.utils.logging import setup_logging


def _compute_debug_dir(output_file: str, enabled: bool) -> Optional[Path]:
    if not enabled:
        return None
    output_path_obj = Path(output_file)
    debug_base_name = output_path_obj.stem
    debug_base_dir = output_path_obj.parent / debug_base_name
    debug_dir = get_unique_debug_dir(debug_base_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    print(f"🔍 DEBUG: Debug files will be saved to: {debug_dir}")
    return debug_dir


def main() -> int:
    # Load .env once here (single entrypoint)
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="scan2epub",
        description="Convert scanned PDFs to clean EPUBs or clean existing EPUBs using Azure AI."
    )
    subparsers = parser.add_subparsers(dest="command")

    # ocr subcommand
    ocr_p = subparsers.add_parser("ocr", help="Run OCR on a PDF (local path or URL) and create an EPUB.")
    ocr_p.add_argument("input_pdf", help="Input PDF file path or publicly accessible URL")
    ocr_p.add_argument("output_epub", help="Output EPUB file path (.epub)")
    ocr_p.add_argument("--language", type=str, default="hu", help="OCR language (default: hu)")
    ocr_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    ocr_p.add_argument("--skip-azure-check", action="store_true", help="Skip lightweight Azure preflight checks")
    ocr_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # clean subcommand
    clean_p = subparsers.add_parser("clean", help="Clean an existing EPUB (OCR artifacts) using Azure OpenAI.")
    clean_p.add_argument("input_epub", help="Input EPUB file path")
    clean_p.add_argument("output_epub", help="Output EPUB file path (.epub)")
    clean_p.add_argument("--save-interim", action="store_true", help="Save interim results to disk (reduces memory)")
    clean_p.add_argument("--status-file", type=str, default=None, help="Write incremental JSONL status to this file")
    # Optional: translate immediately after cleaning
    clean_p.add_argument("--translate-to", type=str, default=None, help="Translate cleaned EPUB to target language code (e.g., en, de)")
    clean_p.add_argument("--translation-provider", type=str, default=None, help="Translation provider to use (default from config)")
    # Translation quality guardrails
    clean_p.add_argument("--allow-noop-translation", action="store_true", help="Allow producing an output even if translation results in no changes")
    clean_p.add_argument("--min-changed-ratio", type=float, default=None, help="Minimum fraction of paragraphs that must change for translation to succeed (0.0-1.0)")
    clean_p.add_argument("--skip-azure-check", action="store_true", help="Skip lightweight Azure preflight checks")
    clean_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    clean_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # convert subcommand (new, preferred)
    conv_p = subparsers.add_parser("convert", help="Convert a PDF (local path or URL) to a cleaned EPUB (full pipeline).")
    conv_p.add_argument("input_pdf", help="Input PDF file path or publicly accessible URL")
    conv_p.add_argument("output_epub", help="Final output EPUB file path (.epub)")
    conv_p.add_argument("--language", type=str, default="hu", help="OCR language (default: hu)")
    conv_p.add_argument("--save-interim", action="store_true", help="Save interim results to disk (reduces memory)")
    conv_p.add_argument("--status-file", type=str, default=None, help="Write incremental JSONL status to this file during cleanup")
    # Optional: perform translation after cleanup
    conv_p.add_argument("--translate-to", type=str, default=None, help="Translate cleaned EPUB to target language code (e.g., en, de)")
    conv_p.add_argument("--translation-provider", type=str, default=None, help="Translation provider to use (default from config)")
    # Translation quality guardrails
    conv_p.add_argument("--allow-noop-translation", action="store_true", help="Allow producing an output even if translation results in no changes")
    conv_p.add_argument("--min-changed-ratio", type=float, default=None, help="Minimum fraction of paragraphs that must change for translation to succeed (0.0-1.0)")
    conv_p.add_argument("--skip-azure-check", action="store_true", help="Skip lightweight Azure preflight checks")
    conv_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    conv_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # pipeline subcommand (deprecated alias; kept for backward compatibility)
    pipe_p = subparsers.add_parser("pipeline", help="(Deprecated) Full pipeline: PDF -> OCR -> cleanup -> EPUB.")
    pipe_p.add_argument("input_pdf", help="Input PDF file path or publicly accessible URL")
    pipe_p.add_argument("output_epub", help="Final output EPUB file path (.epub)")
    pipe_p.add_argument("--language", type=str, default="hu", help="OCR language (default: hu)")
    pipe_p.add_argument("--save-interim", action="store_true", help="Save interim results to disk (reduces memory)")
    pipe_p.add_argument("--status-file", type=str, default=None, help="Write incremental JSONL status to this file during cleanup")
    # Optional: perform translation after cleanup
    pipe_p.add_argument("--translate-to", type=str, default=None, help="Translate cleaned EPUB to target language code (e.g., en, de)")
    pipe_p.add_argument("--translation-provider", type=str, default=None, help="Translation provider to use (default from config)")
    # Translation quality guardrails
    pipe_p.add_argument("--allow-noop-translation", action="store_true", help="Allow producing an output even if translation results in no changes")
    pipe_p.add_argument("--min-changed-ratio", type=float, default=None, help="Minimum fraction of paragraphs that must change for translation to succeed (0.0-1.0)")
    pipe_p.add_argument("--skip-azure-check", action="store_true", help="Skip lightweight Azure preflight checks")
    pipe_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    pipe_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # translate subcommand
    trans_p = subparsers.add_parser("translate", help="Translate an existing EPUB to a target language.")
    trans_p.add_argument("input_epub", help="Input EPUB file path")
    trans_p.add_argument("output_epub", help="Output EPUB file path (.epub)")
    trans_p.add_argument("--to", dest="translate_to", type=str, required=True, help="Target language code (e.g., en, de, hu)")
    trans_p.add_argument("--provider", dest="translation_provider", type=str, default=None, help="Translation provider to use (default from config)")
    # Translation quality guardrails
    trans_p.add_argument("--allow-noop-translation", action="store_true", help="Allow producing an output even if translation results in no changes")
    trans_p.add_argument("--min-changed-ratio", type=float, default=None, help="Minimum fraction of paragraphs that must change for translation to succeed (0.0-1.0)")
    trans_p.add_argument("--status-file", type=str, default=None, help="Write incremental JSONL status to this file")
    trans_p.add_argument("--skip-azure-check", action="store_true", help="Skip lightweight Azure preflight checks")
    trans_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    trans_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # azure-test subcommand
    az_p = subparsers.add_parser("azure-test", help="Run Azure configuration tests and exit.")

    # Parse known args first to allow default subcommand behavior
    import sys
    # If no subcommand provided (first non-flag arg looks like input), default to 'convert'
    argv = sys.argv[1:]
    known_subs = {"ocr", "clean", "pipeline", "convert", "translate", "azure-test"}
    if not argv or (argv[0].startswith("-")):
        # no args or only flags -> show help
        args = parser.parse_args()
    elif argv[0] not in known_subs:
        # Prepend 'convert' as default subcommand
        args = parser.parse_args(["convert"] + argv)
    else:
        args = parser.parse_args()

    # Load typed application config (CLI is the only place that reads env via load_dotenv above)
    app_cfg = AppConfig.from_env_and_ini(args.config if hasattr(args, "config") else None)

    # Initialize logging
    effective_debug = getattr(args, "debug", False) or app_cfg.processing.debug
    setup_logging(debug=effective_debug)
    logger = logging.getLogger("scan2epub.cli")

    # Dispatch
    try:
        if args.command == "azure-test":
            logger.info("Running Azure configuration tests...")
            tester = AzureConfigTester()
            success = tester.run_all_tests()
            return 0 if success else 1

        # Common validations
        output_file = None
        if args.command in ("ocr", "clean", "pipeline", "convert", "translate"):
            output_file = args.output_epub

        if output_file and Path(output_file).suffix.lower() != ".epub":
            logger.error(f"Output file must have .epub extension, but got {Path(output_file).suffix}")
            return 1

        # Compute debug dir if needed
        debug_enabled = effective_debug
        debug_dir = _compute_debug_dir(output_file, debug_enabled) if output_file else None

        if args.command == "ocr":
            input_pdf = args.input_pdf
            language = args.language

            # Preflight (skip if requested or configured)
            skip_preflight = getattr(args, "skip_azure_check", False) or app_cfg.diagnostics.skip_preflight
            if not skip_preflight:
                try:
                    pf = PreflightChecker(app_cfg, None)
                    pf.run_for_ocr(input_pdf)
                except Exception:
                    logger.exception("Preflight check failed for OCR")
                    return 1

            run_ocr_to_epub(
                cfg=app_cfg,
                input_path=input_pdf,
                output_epub=args.output_epub,
                language=language,
                debug=debug_enabled,
                debug_dir=debug_dir,
            )
            logger.info(f"OCR to EPUB conversion completed: {args.input_pdf} -> {args.output_epub}")
            return 0

        elif args.command == "clean":
            input_epub = args.input_epub
            # Normalize status file to absolute path so it is not lost due to CWD changes
            status_path = Path(args.status_file).resolve() if getattr(args, "status_file", None) else None
            # Preflight (skip if requested or configured)
            skip_preflight = getattr(args, "skip_azure_check", False) or app_cfg.diagnostics.skip_preflight
            wants_translation = bool(getattr(args, "translate_to", None))
            if not skip_preflight:
                try:
                    pf = PreflightChecker(app_cfg, status_path)
                    pf.run_for_clean(wants_translation=wants_translation, translate_to=getattr(args, "translate_to", None))
                except Exception:
                    logger.exception("Preflight check failed for clean")
                    return 1

            run_cleanup(
                cfg=app_cfg,
                input_epub=input_epub,
                output_epub=args.output_epub,
                debug=debug_enabled,
                save_interim=args.save_interim or app_cfg.processing.save_interim,
                debug_dir=debug_dir,
                status_file=status_path,
            )
            logger.info(f"EPUB cleanup completed: {args.input_epub} -> {args.output_epub}")

            # Optionally translate the cleaned EPUB in-place to target language
            if getattr(args, "translate_to", None):
                trans_status_path = status_path  # reuse or keep separate
                run_translate(
                    cfg=app_cfg,
                    input_epub=args.output_epub,
                    output_epub=args.output_epub,
                    to_lang=args.translate_to,
                    provider=getattr(args, "translation_provider", None),
                    debug=debug_enabled,
                    debug_dir=debug_dir,
                    status_file=trans_status_path,
                    allow_noop=getattr(args, "allow_noop_translation", None),
                    min_changed_ratio=getattr(args, "min_changed_ratio", None),
                )
                logger.info(f"EPUB translation completed: {args.output_epub} -> {args.output_epub} [{args.translate_to}]")
            return 0

        elif args.command == "translate":
            # Normalize status file to absolute path
            status_path = Path(args.status_file).resolve() if getattr(args, "status_file", None) else None
            # Preflight (skip if requested or configured)
            skip_preflight = getattr(args, "skip_azure_check", False) or app_cfg.diagnostics.skip_preflight
            if not skip_preflight:
                try:
                    pf = PreflightChecker(app_cfg, status_path)
                    pf.run_for_translate(translate_to=getattr(args, "translate_to", None))
                except Exception:
                    logger.exception("Preflight check failed for translate")
                    return 1

            run_translate(
                cfg=app_cfg,
                input_epub=args.input_epub,
                output_epub=args.output_epub,
                to_lang=args.translate_to,
                provider=getattr(args, "translation_provider", None),
                debug=debug_enabled,
                debug_dir=debug_dir,
                status_file=status_path,
                allow_noop=getattr(args, "allow_noop_translation", None),
                min_changed_ratio=getattr(args, "min_changed_ratio", None),
            )
            logger.info(f"EPUB translation completed: {args.input_epub} -> {args.output_epub} [{args.translate_to}]")
            return 0

        elif args.command in ("pipeline", "convert"):
            if args.command == "pipeline":
                logger.warning("The 'pipeline' subcommand is deprecated. Use 'convert' instead.")
            input_pdf = args.input_pdf
            language = args.language
            # Normalize status file to absolute path
            status_path = Path(args.status_file).resolve() if getattr(args, "status_file", None) else None
            # Preflight (skip if requested or configured)
            skip_preflight = getattr(args, "skip_azure_check", False) or app_cfg.diagnostics.skip_preflight
            wants_translation = bool(getattr(args, "translate_to", None))
            if not skip_preflight:
                try:
                    pf = PreflightChecker(app_cfg, status_path)
                    pf.run_for_convert(input_pdf=input_pdf, wants_translation=wants_translation, translate_to=getattr(args, "translate_to", None))
                except Exception:
                    logger.exception("Preflight check failed for convert/pipeline")
                    return 1

            run_full_pipeline(
                cfg=app_cfg,
                input_pdf=input_pdf,
                output_epub=args.output_epub,
                language=language,
                debug=debug_enabled,
                save_interim=args.save_interim or app_cfg.processing.save_interim,
                debug_dir=debug_dir,
                status_file=status_path,
                translate_to=getattr(args, "translate_to", None),
                translate_provider=getattr(args, "translation_provider", None),
                allow_noop_translation=getattr(args, "allow_noop_translation", None),
                min_changed_ratio=getattr(args, "min_changed_ratio", None),
            )
            logger.info(f"Full conversion completed: {args.input_pdf} -> {args.output_epub}")
            return 0

        else:
            parser.error("Unknown command")
            return 1

    except Exception as e:
        logging.getLogger("scan2epub.cli").exception("Unhandled error during execution")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
