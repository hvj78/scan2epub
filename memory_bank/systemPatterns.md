# System Patterns: scan2epub

## Architecture Overview

### Two-Stage Pipeline Pattern
The system uses a clear two-stage processing pipeline:
```
Stage 1: OCR Extraction (PDF → Raw Text)
Stage 2: AI Cleanup (Raw Text → Clean Text)
```

This separation allows:
- Independent optimization of each stage
- Flexibility in processing modes
- Easier debugging and testing
- Future replacement of either stage

### Modular Component Design
```
scan2epub/
├── cli.py                # CLI entrypoint with subcommands (ocr/clean/pipeline/azure-test)
├── pipeline.py           # Orchestration functions: run_ocr_to_epub, run_cleanup, run_full_pipeline
├── config.py             # Typed application config (AppConfig + Azure configs + Processing)
├── config_manager.py     # INI-backed defaults and user config handling
├── utils/
│   ├── logging.py        # Central logging setup
│   └── errors.py         # Typed exception hierarchy
├── azure/
│   ├── storage.py        # Azure Blob uploads + SAS URL generation and cleanup
│   └── diagnostics.py    # Azure environment/config test suite (azure-test)
├── ocr/
│   └── azure_cu.py       # Azure Content Understanding OCR client + text extraction
└── epub/
    ├── builder.py        # Basic EPUB building from text
    └── cleaner.py        # EPUB cleaning via Azure OpenAI (chunking, LLM calls, HTML reconstruct)
```

Each module has a single responsibility and clear interfaces.

## Key Technical Decisions

### 1. Azure Services Integration
**Decision**: Use Azure AI services for both OCR and cleanup; Azure Blob for local file upload-to-URL
**Rationale**: 
- High quality results, especially for Hungarian
- Managed service reduces complexity
- Scalable without infrastructure concerns
**Trade-offs**: 
- Cost per processing
- Internet dependency
- Vendor lock-in

### 2. PDF Input Sources: URL or Local Path
**Decision**: Accept local file paths or URLs. Local files are uploaded to Azure Blob and converted to SAS URLs.
**Rationale**:
- CU API requires a URL; Blob upload bridges local files → URL
- Improves UX vs requiring user-hosted URLs
**Trade-offs**:
- Requires valid Storage connection string and container
- Temporary cloud storage step added

### 3. Chunked Text Processing
**Decision**: Split text into ~3000 token "tokens" (≈2 chars per token heuristic) for LLM processing
**Pattern**:
```python
chunks = chunk_text(text, max_tokens_per_chunk=3000)  # paragraphs -> sentences -> forced split
```
**Rationale**:
- Respects LLM limits conservatively
- Prefers paragraph boundaries, then sentences
- Prevents excessive mid-sentence splits

### 4. Memory Management Strategy
**Decision**: Offer --save-interim for large files; optional debug directories for artifacts
**Pattern**:
- Process chapters/chunks individually
- Save interim JSON results when requested
- Use debug_dir for extracted EPUB and LLM req/resp
**Rationale**:
- Reduces memory footprint on large books
- Improves debuggability and post-mortem analysis

## Design Patterns in Use

### 1. Configuration Object Pattern
```python
@dataclass
class AzureConfig:
    api_key: str
    endpoint: str
    # ... all config in one place
```
Benefits:
- Type safety
- Easy validation
- Clear dependencies

### 2. Builder Pattern (EPUBBuilder)
```python
builder = EPUBBuilder()
builder.set_metadata(...)
builder.add_chapter(...)
builder.build_epub(output_path)
```
Benefits:
- Fluent interface
- Separation of construction steps
- Reusable for different scenarios

### 3. Strategy Pattern (Processing Modes)
The CLI implements separate strategies via subcommands:
- pipeline: full pipeline
- ocr: OCR only (PDF → EPUB)
- clean: cleanup only (EPUB → cleaned EPUB)
- azure-test: environment/config diagnostics

### 4. Template Method Pattern (Cleanup Prompt)
```python
def create_cleanup_prompt():
    return """[Fixed template with Hungarian instructions]"""
```
The prompt serves as a template that guides AI behavior consistently.

## Component Relationships

### Data Flow Architecture
```
PDFOCRProcessor
    ↓ (OCR Result)
EPUBBuilder
    ↓ (Interim EPUB)
EPUBOCRCleaner
    ↓ (Cleaned Text)
EPUBBuilder
    ↓ (Final EPUB)
```

### Dependency Structure
- cli.py depends on pipeline and config
- pipeline.py depends on ocr.azure_cu, epub.builder, epub.cleaner, azure.storage, utils.errors
- azure.storage uses Azure SDK; config_manager provides INI defaults; config defines typed configs
- External dependencies declared in pyproject.toml

## Critical Implementation Paths

### 1. OCR Processing Path
```
run_ocr_to_epub(cfg, input_path, output_epub, language, debug, debug_dir)
  → if local: AzureStorageHandler.upload_pdf() → SAS URL
  → PDFOCRProcessor.process_pdf(pdf_url)
      → _send_analyze_request(url) → returns operation_id
      → _get_analyze_result(operation_id) → polls until Succeeded
  → extract_text_from_ocr_result(result) → markdown concatenation
  → EPUBBuilder.set_metadata(...); add_chapter(...); build_epub(output_epub)
```

### 2. Cleanup Processing Path
```
run_cleanup(cfg, input_epub, output_epub, debug, save_interim, debug_dir)
  → EPUBOCRCleaner(..., azure_openai_cfg=cfg.azure_openai).clean_epub()
     → extract_epub_content(): unzip + ebooklib + BeautifulSoup
     → analyze_ocr_artifacts(): regex metrics
     → chunk_text(): paragraphs → sentences → forced split
     → clean_text_with_llm(): Azure OpenAI chat.completions
     → reconstruct_html(): paragraphs/headings heuristic
     → create_cleaned_epub(): build final EPUB via ebooklib
```

### 3. Error Handling Path
- Configuration validation at startup
- Retry logic with exponential backoff
- Graceful degradation to original text
- User-friendly error messages

## Performance Patterns

### Async Operation Handling
```python
operation_id = self._send_analyze_request(pdf_url)
# Polling with backoff and status prints
for attempt in range(max_retries):
    result = requests.get(result_url)
    status = result["status"]
    if status == "Succeeded": ...
    elif status in ["Running", "NotStarted"]:
        time.sleep(retry_delay)
```

### Progress Indication
- tqdm progress bar for Azure Blob upload
- Logger info for chapter processing and artifacts
- Console prints for CU status polling

### Resource Optimization
- Lazy loading of content
- Streaming where possible
- Cleanup of temporary files
- Memory monitoring with psutil

## Error Handling Patterns

### Defensive Programming
```python
if not os.getenv('AZURE_OPENAI_API_KEY'):
    raise ValueError("Missing required environment variable")
```

### Graceful Degradation
```python
try:
    cleaned_text = self.clean_text_with_llm(chunk)
except Exception as e:
    print(f"Failed to clean chunk, using original")
    cleaned_text = chunk
```

### Comprehensive Logging
- Configuration issues logged clearly
- API errors with context
- Processing statistics
- Debug mode for detailed traces

## Hungarian Language Patterns

### Text Processing Rules
1. **Hyphenation Handling**: "szó-\ntag" → "szótag"
2. **Compound Words**: Preserve Hungarian compounds
3. **Character Encoding**: UTF-8 throughout
4. **Special Characters**: Preserve ő, ű, etc.

### Cleanup Prompt Structure
- Instructions in Hungarian
- Examples use Hungarian text
- Rules specific to Hungarian typography
- Preservation of Hungarian grammar

## Future-Proofing Patterns

### Abstraction Layers
- OCR backend could be swapped
- LLM provider could change
- EPUB library is isolated
- Configuration is centralized

### Extension Points
- New processing modes easy to add
- Additional languages via new prompts
- Alternative storage backends possible
- Plugin architecture feasible

### Migration Paths
- Azure → Local AI models
- URL input → Direct file upload
- Single file → Batch processing
- CLI → GUI interface
