# Technical Architecture

## System Overview

scan2epub is built as a modular Python application with three main components that work together to process PDFs into clean EPUBs.

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   PDF URL   │ --> │ pdf_ocr_processor│ --> │ epub_builder │
└─────────────┘     └──────────────────┘     └──────────────┘
                              |                        |
                              v                        v
                    ┌──────────────────┐     ┌──────────────┐
                    │  Azure Content   │     │ Initial EPUB │
                    │  Understanding   │     └──────────────┘
                    └──────────────────┘              |
                                                      v
                                            ┌──────────────────┐
                                            │ EPUBOCRCleaner  │
                                            └──────────────────┘
                                                      |
                                                      v
                                            ┌──────────────────┐
                                            │  Azure GPT-4    │
                                            └──────────────────┘
                                                      |
                                                      v
                                            ┌──────────────────┐
                                            │  Clean EPUB     │
                                            └──────────────────┘
```

## Core Components

### 1. scan2epub.py (Main Orchestrator)
- Entry point for the application
- Handles command-line argument parsing
- Manages the processing pipeline
- Contains the `EPUBOCRCleaner` class for cleanup operations

**Key Classes:**
- `AzureConfig`: Configuration dataclass for Azure OpenAI settings
- `EPUBOCRCleaner`: Main class for cleaning OCR artifacts

**Key Methods:**
- `main()`: CLI entry point and pipeline orchestration
- `clean_epub()`: Main method to clean an EPUB file
- `clean_text_with_llm()`: Processes text chunks with Azure GPT-4
- `chunk_text()`: Splits text into manageable chunks for LLM processing

### 2. pdf_ocr_processor.py (OCR Module)
- Handles PDF to text extraction using Azure AI Content Understanding
- Processes PDFs from publicly accessible URLs
- Extracts structured text with markdown formatting

**Key Class:**
- `PDFOCRProcessor`: Manages Azure Content Understanding API interactions

**Key Methods:**
- `process_pdf()`: Main method to analyze a PDF via URL
- `_send_analyze_request()`: Initiates async OCR analysis
- `_get_analyze_result()`: Polls for analysis completion
- `extract_text_from_ocr_result()`: Extracts markdown text from results

### 3. epub_builder.py (EPUB Construction)
- Creates EPUB files from text content
- Handles metadata and chapter organization
- Converts plain text to proper HTML structure

**Key Class:**
- `EPUBBuilder`: Constructs EPUB files using ebooklib

**Key Methods:**
- `set_metadata()`: Sets book metadata (title, author, language)
- `add_chapter()`: Adds chapters with HTML formatting
- `build_epub()`: Finalizes and writes the EPUB file

## Data Flow

### Full Pipeline Mode
1. User provides PDF URL
2. `PDFOCRProcessor` sends URL to Azure Content Understanding
3. Azure returns OCR results with markdown-formatted text
4. `EPUBBuilder` creates initial EPUB from OCR text
5. `EPUBOCRCleaner` extracts content from EPUB
6. Text is chunked and sent to Azure GPT-4 for cleanup
7. Cleaned text is reconstructed into HTML
8. Final clean EPUB is created

### OCR-Only Mode
1. PDF URL → Azure Content Understanding
2. OCR results → EPUBBuilder
3. Output: EPUB with preserved original structure

### Cleanup-Only Mode
1. Existing EPUB → EPUBOCRCleaner
2. Text extraction and chunking
3. Azure GPT-4 processing
4. Output: Cleaned EPUB

## Dependencies

### Python Packages
- **openai** (>=1.0.0): Azure OpenAI SDK
- **python-dotenv** (>=1.0.0): Environment variable management
- **ebooklib** (>=0.18): EPUB file manipulation
- **beautifulsoup4** (>=4.12.0): HTML parsing
- **lxml** (>=4.9.0): XML processing
- **requests** (>=2.31.0): HTTP requests for API calls
- **tqdm** (>=4.66.0): Progress bars
- **psutil** (>=5.9.0): System and process utilities

### External Services
- **Azure AI Content Understanding**: For OCR processing
- **Azure OpenAI (GPT-4)**: For text cleanup and optimization

## Text Processing Strategy

### Chunking Algorithm
- Maximum tokens per chunk: 3000 (configurable)
- Rough estimation: 1 token ≈ 4 characters for Hungarian
- Splits by paragraphs first, then sentences if needed
- Maintains context across chunk boundaries

### OCR Artifact Detection
The system identifies common OCR issues:
- Excessive line breaks
- Hyphenated words across lines
- Single-line paragraphs
- Isolated page numbers
- Unnaturally short lines

### LLM Cleanup Prompt
The cleanup prompt is specifically designed for Hungarian text:
- Removes unnecessary line breaks and page separations
- Merges hyphenated words (e.g., "szó-\ntag" → "szótag")
- Preserves paragraph structure
- Maintains original meaning without content changes

## Error Handling

- **Retry Logic**: Configurable retries for API calls (default: 3)
- **Graceful Degradation**: Falls back to original text on processing failure
- **Memory Management**: Optional --save-interim flag for large files
- **Backup Creation**: Automatic backup before processing EPUBs
