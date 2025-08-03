Refactor recommendations for a cleaner, testable Python 3.12 CLI codebase

3th Aug. 2025.
Created by Horizon Beta LLM

Overview
The project has a solid start with clear responsibilities:
- scan2epub.py orchestrates the pipeline (OCR only, cleanup only, or full).
- pdf_ocr_processor.py calls Azure Content Understanding for OCR and returns markdown content.
- epub_builder.py builds simple EPUBs from text.
- azure_storage_handler.py manages temporary uploads to Azure Blob Storage for local files.
- config_manager.py provides INI-based runtime config.
- azure_config_tester.py validates environment and Azure connectivity.

Key improvement opportunities:
- Clear separation of concerns and boundaries
- Dependency injection for testability (replace hard-coded globals and env reads at import time)
- Consistent configuration flow and typed settings
- Logging and error taxonomy
- CLI structured with subcommands and centralized validation
- Packaging layout and module naming
- Test strategy and lightweight tooling

Minimal package structure (src layout)
Adopt a package structure that separates library code from the CLI entrypoint and supports later web backend use.

Proposed:
- src/
  - scan2epub/
    - __init__.py
    - cli.py                 # Typer/argparse CLI with subcommands
    - pipeline.py            # Orchestrator functions for each mode
    - config.py              # Typed config (pydantic optional) + .env loader
    - ocr/
      - __init__.py
      - azure_cu.py          # PDFOCRProcessor (renamed, no dotenv here)
    - epub/
      - __init__.py
      - builder.py           # EPUBBuilder
      - cleaner.py           # EPUBOCRCleaner (LLM cleaning; HTML reconstruction)
    - azure/
      - __init__.py
      - storage.py           # AzureStorageHandler
      - diagnostics.py       # AzureConfigTester
    - utils/
      - __init__.py
      - io.py                # temp dirs, debug helpers (_get_unique_debug_dir)
      - errors.py            # custom exceptions
      - logging.py           # setup_logging()
- tests/
  - unit/ ...                # pure logic tests
  - integration/ ...         # Azure mocked/recorded tests
- scan2epub.ini              # remains in project root
- .env.template
- README.md

Keep names short and descriptive. Group domains into subpackages (ocr, epub, azure, utils).

Configuration and environment handling
Issues:
- dotenv is imported and executed in multiple modules; side effects at import time make tests harder.
- Azure settings spread across .env and runtime.

Recommendations:
1) Single configuration entrypoint:
   - Only the CLI loads .env once and builds a Config object.
   - Pass Config down into pipeline/services; do not read os.getenv in library modules.
2) Typed config class:
   - Option A (minimal): Keep ConfigManager (INI) but add a simple dataclass AppConfig whose fields are constructed from ConfigManager + os.environ. This centralizes defaults and validation.
   - Option B (slightly richer): Use pydantic-settings for typed env+INI merge and validation. If “avoid overcomplication,” use Option A now and revisit later.

Example minimal typed config:
- config.py
  - load_dotenv() in CLI only
  - class AzureOpenAIConfig(dataclass)
  - class AzureCUConfig(dataclass)
  - class AzureStorageConfig(dataclass)
  - class ProcessingConfig(dataclass)
  - class AppConfig(dataclass) with the above subconfigs and methods from_env_and_ini(path)

Dependency injection and boundaries
- Do not instantiate SDK clients at import time.
- Create simple provider functions that accept configuration and return clients.
- Pass dependencies explicitly into functions/classes:
  - AzureCUClient (requests session + base URL/key) into OCR service.
  - AzureOpenAI client into EPUB cleaner.
  - BlobService into storage handler.

This makes unit tests trivial with mocks/fakes.

CLI refactor (subcommands, validation)
Current argparse flags combine multiple modes. A clearer interface is subcommands:
- scan2epub ocr INPUT.pdf OUTPUT.epub [--language hu --debug]
- scan2epub clean INPUT.epub OUTPUT.epub [--debug --save-interim]
- scan2epub pipeline INPUT.pdf OUTPUT.epub [--language hu --debug --save-interim]
- scan2epub azure-test

Benefits:
- Clearer UX and simpler argument validation per command.
- Easier to expose later HTTP endpoints with same orchestration functions.

Use argparse (already present) or Typer (minimal, adds rich help). Since “keep it simple,” argparse is fine; but Typer improves DX with type hints and colored help. Either is acceptable; choose argparse to avoid new deps.

Error handling and exceptions
Define a small error taxonomy:
- class Scan2EpubError(Exception)
  - class ConfigError(Scan2EpubError)
  - class StorageError(Scan2EpubError)
  - class OCRError(Scan2EpubError)
  - class LLMError(Scan2EpubError)
  - class EPUBError(Scan2EpubError)

Raise these instead of generic Exception/ValueError. Exit codes and messages are then consistent in CLI.

Logging
Replace print with logging:
- utils.logging.setup_logging(debug: bool) configures a root logger, console handler.
- Use logger.info/debug/warning/error.
- Keep the helpful emoji in debug if desired; but avoid in normal logs.

Debug directory lifecycle
- Move _get_unique_debug_dir to utils.io.
- All services accept debug parameters and a debug_dir Path, but creation and ownership happen in the CLI or pipeline, never inside the service (pass in Path).
- Ensure temp dirs and interim files are removed on success or retained only when debug is enabled.

EPUB cleaning separation
EPUBOCRCleaner mixes EPUB parsing, LLM cleaning, and HTML rebuilding. Split into composable functions:
- epub.extract(epub_path) -> ExtractedBook(content_items, metadata, temp_dir)
- cleaner.analyze(text) -> dict
- cleaner.chunk(text, token_limit) -> list[str]
- cleaner.clean_chunks(chunks, client) -> list[str]
- cleaner.rebuild_html(cleaned_text) -> html str
- epub.build(original_metadata, cleaned_items, output_path)

Keep pure functions where possible to simplify tests. Ensure BeautifulSoup parser is explicit (features="lxml") for consistency.

Azure Content Understanding OCR
- pdf_ocr_processor._send_analyze_request assumes a URL. Keep that, but implement a dedicated upload flow at pipeline level:
  - If input is local: storage.upload_pdf() -> sas_url -> pass to OCR.
- Extract only what you need (markdown) but allow optional fallback to paragraphs for robustness.

Storage handler
- azure_storage_handler currently reads env and constructs clients. Refactor to:
  - Accept AzureStorageConfig + BlobServiceClient instance passed from factory.
  - Move download_all_blobs and is_local_file_blob to optional utilities or remove until needed.
- Ensure cleanup semantics are controlled from pipeline; do not perform cleanup in finally if debug=True.

Pipeline orchestrator
Introduce pipeline.py with three functions that encapsulate the current main branching:
- run_ocr_to_epub(cfg, input, output, language, debug_dir)
- run_cleanup(cfg, input_epub, output_epub, debug_dir, save_interim)
- run_full_pipeline(cfg, input_pdf, output_epub, language, debug_dir, save_interim)

Each returns a small result dataclass with file paths and counters. The CLI only parses args and calls these.

Type hints and return types
- Enforce typing on all public functions.
- Where third-party types are loose, use TypedDict or dataclasses to shape your internal data (e.g., ContentItem with id, file_name, title, content, html_content).

Testing approach (minimal)
- Unit tests:
  - cleaner.chunk_text and analyze_ocr_artifacts
  - reconstruct_html (determinism, headings vs paragraphs)
  - epub_builder.add_chapter and build_epub with a temp dir
  - config assembly from env + INI defaults
- Integration tests (optional):
  - Storage handler with mocked BlobServiceClient
  - OCR client with requests_mock to simulate polling
  - Azure OpenAI client interactions with a fake client
- Use pytest. No heavy fixtures required.

Tooling (minimal, simple)
- Add ruff (linter/formatter), black optional if you prefer. Ruff can format now.
- Add mypy with relaxed config; at least check obvious typing issues.
- Add pre-commit with ruff and end-of-file-fixer. Keep it light.

Concrete refactor checklist
1) Centralize config:
   - Create src/scan2epub/config.py with dataclasses:
     - AzureOpenAIConfig, AzureCUConfig, AzureStorageConfig, ProcessingConfig, AppConfig
   - Build AppConfig from:
     - os.environ (loaded once in CLI)
     - ConfigManager (INI) for user preferences (debug, save_interim, limits, container)
   - Remove load_dotenv() calls from library modules.

2) Introduce a small errors module:
   - utils/errors.py with the exception classes listed above.
   - Replace bare Exception/ValueError in services with specific errors.

3) Replace print with logging:
   - utils/logging.py: setup_logging(debug: bool)
   - In CLI, call setup_logging(args.debug or cfg.processing.debug)

4) Split EPUBOCRCleaner responsibilities:
   - epub/cleaner.py exposes functions/classes:
     - analyze(text) -> dict
     - chunker(token_limit).chunk(text)
     - cleaner(client, prompt, max_tokens).clean(text) -> str
     - reconstruct_html(cleaned_text) -> str
   - Keep state minimal. Inject openai client.

5) Dedicated pipeline module:
   - Extract the big branching from scan2epub.py main() into pipeline.py with three functions.
   - Main/CLI only does:
     - parse args -> build AppConfig -> compute debug_dir -> call pipeline -> print summary.

6) Storage handler DI:
   - azure/storage.py constructor accepts BlobServiceClient or a factory function and AzureStorageConfig.
   - No direct env reads here.

7) Rename and relocate:
   - pdf_ocr_processor.py -> ocr/azure_cu.py
   - epub_builder.py -> epub/builder.py
   - azure_storage_handler.py -> azure/storage.py
   - azure_config_tester.py -> azure/diagnostics.py
   - scan2epub.py -> src/scan2epub/cli.py

8) CLI subcommands:
   - argparse subparsers: ocr, clean, pipeline, azure-test
   - Each subcommand validates its own args and calls pipeline functions
   - Keep options identical to README while improving help text

9) Minor logic improvements:
   - In EPUB cleaning, when generating titles/headings, avoid the heuristic “len < 100 and not endswith('.')” driving h2; consider a more conservative approach or pass through headings if present in original HTML.
   - In clean_text_with_llm, when dumping response for debug, response.model_dump_json() already returns a JSON string; avoid json.dump of a JSON string to prevent double-encoding. Dump response.to_dict() or parse the JSON string first.
   - Ensure BeautifulSoup uses “lxml” parser and handle encoding explicitly.
   - In create_cleaned_epub, ensure nav/toc.ncx/content.opf are excluded consistently, as you do earlier.

10) README adjustments:
   - Document subcommands and config precedence (CLI flags override INI; INI overrides env defaults where applicable).
   - Explain debug_dir behavior and saved artifacts layout.

11) Add minimal CI (optional but simple):
   - GitHub Actions workflow:
     - Setup Python 3.12
     - pip install -r requirements.txt; pip install ruff pytest
     - ruff check .; pytest -q

12) Keep dependencies minimal:
   - Keep argparse.
   - Optionally add ruff and pytest as dev-only. Avoid pydantic for now unless you want stricter validation.

Examples of small changes you can implement now
- Move load_dotenv() to CLI only, and pass configuration into services.
- Introduce a small errors.py and replace generic exceptions in azure_storage_handler.py and pdf_ocr_processor.py.
- Add a utils/io.py with _get_unique_debug_dir and reuse in cli/pipeline.
- Refactor the main branching into three small functions in scan2epub.py for readability even before moving to src layout.

Potential follow-ups for future web backend
- The pipeline functions will be reusable from a FastAPI/Quart app later.
- The same AppConfig concept can be built from environment and secrets.
- Return structured results, not just printed logs, to support HTTP responses.

Summary
These changes keep the codebase simple while dramatically improving structure, clarity, and testability:
- One config entrypoint, explicit dependencies, no env side-effects in library modules
- Clear module boundaries and a pipeline orchestrator
- Subcommand-based CLI and logging
- Lightweight testing and linting

This yields a maintainable CLI-first project that can evolve into a backend service cleanly without major rewrites.