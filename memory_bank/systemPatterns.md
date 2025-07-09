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
├── pdf_ocr_processor.py  # OCR concerns only
├── epub_builder.py       # EPUB construction only
└── scan2epub.py         # Orchestration + Cleanup
```

Each module has a single responsibility and clear interfaces.

## Key Technical Decisions

### 1. Azure Services Integration
**Decision**: Use Azure AI services for both OCR and cleanup
**Rationale**: 
- High quality results, especially for Hungarian
- Managed service reduces complexity
- Scalable without infrastructure concerns
**Trade-offs**: 
- Cost per processing
- Internet dependency
- Vendor lock-in

### 2. URL-Based PDF Input
**Decision**: Require PDFs to be accessible via public URL
**Rationale**:
- Azure Content Understanding API requires URLs
- Avoids large file uploads in the application
- Simplifies architecture
**Trade-offs**:
- User must handle file hosting
- Additional step in workflow

### 3. Chunked Text Processing
**Decision**: Split text into ~3000 token chunks for LLM processing
**Pattern**:
```python
def chunk_text(text):
    # Split by paragraphs first
    # Then by sentences if needed
    # Force split at character limit
```
**Rationale**:
- Respects LLM token limits
- Maintains context within chunks
- Prevents mid-sentence splits

### 4. Memory Management Strategy
**Decision**: Offer --save-interim flag for large files
**Pattern**:
- Process chunks individually
- Save intermediate results to disk
- Clear memory after each chunk
**Rationale**:
- Handles books of any size
- Prevents memory exhaustion
- Allows process resumption

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
The main() function implements different strategies:
- Full pipeline strategy
- OCR-only strategy  
- Cleanup-only strategy

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
- `scan2epub.py` depends on all other modules
- `pdf_ocr_processor.py` is independent
- `epub_builder.py` is independent
- External dependencies managed via requirements.txt

## Critical Implementation Paths

### 1. OCR Processing Path
```
process_pdf(url)
  → _send_analyze_request(url)
    → Azure API call (async)
  → _get_analyze_result(operation_id)
    → Poll until complete
  → extract_text_from_ocr_result()
    → Return markdown text
```

### 2. Cleanup Processing Path
```
clean_epub(input_path)
  → extract_epub_content()
    → Parse with BeautifulSoup
  → analyze_ocr_artifacts()
    → Identify issues
  → chunk_text()
    → Split for LLM
  → clean_text_with_llm()
    → Azure GPT-4 processing
  → reconstruct_html()
    → Build clean structure
  → create_cleaned_epub()
    → Generate final file
```

### 3. Error Handling Path
- Configuration validation at startup
- Retry logic with exponential backoff
- Graceful degradation to original text
- User-friendly error messages

## Performance Patterns

### Async Operation Handling
```python
# Submit request
operation_id = self._send_analyze_request(pdf_url)

# Poll for completion
while status not in ["Succeeded", "Failed"]:
    time.sleep(retry_delay)
    result = self._get_analyze_result(operation_id)
```

### Progress Indication
- tqdm for visual progress bars
- Chunk-by-chunk processing feedback
- Status messages at each stage

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
