import argparse
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from scan2epub.config_manager import ConfigManager
from scan2epub.pipeline import run_ocr_to_epub, run_cleanup, run_full_pipeline
from scan2epub.azure.diagnostics import AzureConfigTester
from scan2epub.utils.io import get_unique_debug_dir


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
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ocr subcommand
    ocr_p = subparsers.add_parser("ocr", help="Run OCR on a PDF (local path or URL) and create an EPUB.")
    ocr_p.add_argument("input_pdf", help="Input PDF file path or publicly accessible URL")
    ocr_p.add_argument("output_epub", help="Output EPUB file path (.epub)")
    ocr_p.add_argument("--language", type=str, default="hu", help="OCR language (default: hu)")
    ocr_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    ocr_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # clean subcommand
    clean_p = subparsers.add_parser("clean", help="Clean an existing EPUB (OCR artifacts) using Azure OpenAI.")
    clean_p.add_argument("input_epub", help="Input EPUB file path")
    clean_p.add_argument("output_epub", help="Output EPUB file path (.epub)")
    clean_p.add_argument("--save-interim", action="store_true", help="Save interim results to disk (reduces memory)")
    clean_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    clean_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # pipeline subcommand
    pipe_p = subparsers.add_parser("pipeline", help="Full pipeline: PDF -> OCR -> cleanup -> EPUB.")
    pipe_p.add_argument("input_pdf", help="Input PDF file path or publicly accessible URL")
    pipe_p.add_argument("output_epub", help="Final output EPUB file path (.epub)")
    pipe_p.add_argument("--language", type=str, default="hu", help="OCR language (default: hu)")
    pipe_p.add_argument("--save-interim", action="store_true", help="Save interim results to disk (reduces memory)")
    pipe_p.add_argument("--config", type=str, default=None, help="Path to configuration file (default: scan2epub.ini)")
    pipe_p.add_argument("--debug", action="store_true", help="Enable debug output")

    # azure-test subcommand
    az_p = subparsers.add_parser("azure-test", help="Run Azure configuration tests and exit.")

    args = parser.parse_args()

    # Load configuration (INI)
    cfg = ConfigManager(args.config if hasattr(args, "config") else None)

    # Dispatch
    try:
        if args.command == "azure-test":
            print("Running Azure configuration tests...")
            tester = AzureConfigTester()
            success = tester.run_all_tests()
            return 0 if success else 1

        # Common validations
        output_file = None
        if args.command == "ocr":
            output_file = args.output_epub
        elif args.command == "clean":
            output_file = args.output_epub
        elif args.command == "pipeline":
            output_file = args.output_epub

        if output_file and Path(output_file).suffix.lower() != ".epub":
            print(f"Error: Output file must have .epub extension, but got {Path(output_file).suffix}")
            return 1

        # Compute debug dir if needed
        debug_enabled = getattr(args, "debug", False) or cfg.debug
        debug_dir = _compute_debug_dir(output_file, debug_enabled) if output_file else None

        if args.command == "ocr":
            input_pdf = args.input_pdf
            language = args.language
            run_ocr_to_epub(
                cfg=cfg,
                input_path=input_pdf,
                output_epub=args.output_epub,
                language=language,
                debug=debug_enabled,
                debug_dir=debug_dir,
            )
            print(f"OCR to EPUB conversion completed: {args.input_pdf} -> {args.output_epub}")
            return 0

        elif args.command == "clean":
            input_epub = args.input_epub
            run_cleanup(
                cfg=cfg,
                input_epub=input_epub,
                output_epub=args.output_epub,
                debug=debug_enabled,
                save_interim=args.save_interim or cfg.save_interim,
                debug_dir=debug_dir,
            )
            print(f"EPUB cleanup completed: {args.input_epub} -> {args.output_epub}")
            return 0

        elif args.command == "pipeline":
            input_pdf = args.input_pdf
            language = args.language
            run_full_pipeline(
                cfg=cfg,
                input_pdf=input_pdf,
                output_epub=args.output_epub,
                language=language,
                debug=debug_enabled,
                save_interim=args.save_interim or cfg.save_interim,
                debug_dir=debug_dir,
            )
            print(f"Full pipeline completed: {args.input_pdf} -> {args.output_epub}")
            return 0

        else:
            parser.error("Unknown command")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
