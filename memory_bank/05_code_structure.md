# Code Structure

## File Organization

```
scan2epub/
├── .clineignore          # Cline-specific ignore file
├── .clinerules           # Cline-specific rules and memory bank configuration
├── .env                  # Environment variables (user created)
├── .env.template         # Template for environment configuration
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
├── scan2epub.py         # Main entry point and orchestrator
├── pdf_ocr_processor.py # PDF OCR processing module
├── epub_builder.py      # EPUB construction module
├── docs/                # Documentation directory
│   └── azure-setup.md   # Azure setup documentation
├── memory_bank/         # Comprehensive project knowledge base
│   ├── INDEX.md         # Navigation hub
│   ├── README.md        # Memory bank guide
│   ├── 01_project_overview.md
│   ├── 02_technical_architecture.md
│   ├── 03_azure_configuration.md
│   ├── 04_usage_guide.md
│   ├── 05_code_structure.md
│   ├── 06_limitations_issues.md
│   └── 07_roadmap.md
└── personal/            # Personal/private files (gitignored)
```

## Module Details

### scan2epub.py

**Purpose**: Main orchestrator that manages the entire pipeline and contains the EPUB cleanup logic.

**Key Components**:

```python
@dataclass
class AzureConfig:
    """Configuration for Azure OpenAI API"""
    api_key: str
    endpoint: str
    api_version: str
    deployment_name: str
    max_tokens_per_chunk: int
    temperature: float
    max_tokens_response: int
    max_retries: int
    retry_delay: int
```

```python
class EPUBOCRCleaner:
    """Main class for cleaning OCR artifacts from EPUB files"""
    
    def __init__(self)
    def _load_azure_config() -> AzureConfig
    def _initialize_azure_client() -> openai.AzureOpenAI
    def extract_epub_content(epub_path: str) -> Tuple[Dict, str]
    def analyze_ocr_artifacts(text: str) -> Dict[str, int]
    def create_cleanup_prompt() -> str
    def chunk_text(text: str) -> List[str]
    def clean_text_with_llm(text: str) -> str
    def reconstruct_html(cleaned_text: str, original_html: str) -> str
    def create_cleaned_epub(original_data: Dict, cleaned_content: List[Dict], output_path: str, debug: bool = False)
    def clean_epub(input_path: str, output_path: str = None, debug: bool = False, save_interim: bool = False)
```

**Main Function**:
- Parses command-line arguments
- Determines processing mode (full, OCR-only, cleanup-only)
- Orchestrates the appropriate pipeline
- Handles errors and provides user feedback

### pdf_ocr_processor.py

**Purpose**: Handles PDF to text extraction using Azure AI Content Understanding service.

**Key Components**:

```python
class PDFOCRProcessor:
    """Processes PDF files using Azure AI Content Understanding for OCR"""
    
    def __init__(self)
    def _send_analyze_request(pdf_path: str) -> str
    def _get_analyze_result(operation_id: str) -> Dict[str, Any]
    def process_pdf(pdf_url: str) -> Dict[str, Any]
    def extract_text_from_ocr_result(analyze_result: Dict[str, Any]) -> str
```

**Configuration**:
- Endpoint: `AZURE_CU_ENDPOINT`
- API Key: `AZURE_CU_API_KEY`
- API Version: `2025-05-01-preview`
- Analyzer ID: `prebuilt-documentAnalyzer`

**Important Notes**:
- Requires PDF to be accessible via public URL
- Uses async operation pattern (submit → poll → retrieve)
- Extracts markdown-formatted content from results

### epub_builder.py

**Purpose**: Creates EPUB files from text content with proper structure and formatting.

**Key Components**:

```python
class EPUBBuilder:
    """Builds an EPUB file from structured text content"""
    
    def __init__(self)
    def set_metadata(title: str, author: str, language: str = 'en', identifier: str = 'unknown')
    def add_chapter(title: str, content: str, file_name: str = None)
    def build_epub(output_path: str)
```

**Features**:
- Automatic HTML generation from plain text
- Smart paragraph/heading detection
- Metadata management
- Chapter organization
- EPUB 2/3 compatible output

## Key Algorithms

### Text Chunking (in EPUBOCRCleaner)
```python
# Rough estimation: 1 token ≈ 4 characters for Hungarian
max_chars = self.config.max_tokens_per_chunk * 2

# Priority order:
1. Split by paragraphs (double newlines)
2. If paragraph too long, split by sentences
3. If sentence too long, force split at character limit
```

### OCR Artifact Detection
```python
artifacts = {
    'excessive_line_breaks': len(re.findall(r'\n\s*\n\s*\n', text)),
    'hyphenated_words': len(re.findall(r'\w+-\s*\n\s*\w+', text)),
    'single_line_paragraphs': len(re.findall(r'\n\s*\S[^\n]*\n\s*\n', text)),
    'page_numbers': len(re.findall(r'\n\s*\d+\s*\n', text)),
    'short_lines': len([line for line in text.split('\n') if 0 < len(line.strip()) < 30])
}
```

### HTML Reconstruction
1. Split cleaned text into paragraphs
2. Identify headings (short, no period)
3. Wrap in appropriate HTML tags
4. Create valid XHTML structure for EPUB

## Processing Flow

### Full Pipeline
```
1. main() receives PDF URL and output path
2. PDFOCRProcessor.process_pdf(url)
   - Sends URL to Azure Content Understanding
   - Polls for completion
   - Returns OCR result
3. PDFOCRProcessor.extract_text_from_ocr_result()
   - Extracts markdown content
4. EPUBBuilder creates interim EPUB
   - Sets metadata
   - Adds chapter with OCR text
   - Builds EPUB file
5. EPUBOCRCleaner.clean_epub()
   - Extracts content from interim EPUB
   - Analyzes OCR artifacts
   - Chunks text for LLM processing
   - Sends to Azure GPT-4
   - Reconstructs HTML
   - Creates final EPUB
6. Cleanup interim files
```

### Error Handling Strategy

1. **Configuration Errors**:
   - Check environment variables on startup
   - Raise ValueError with clear message

2. **API Errors**:
   - Retry with exponential backoff
   - Fall back to original text on failure
   - Log detailed error information

3. **Memory Errors**:
   - Offer --save-interim flag
   - Process chunks individually
   - Clear large objects after use

4. **File Errors**:
   - Create automatic backups
   - Validate file formats
   - Handle missing/corrupt files gracefully

## Hungarian Language Optimization

### Cleanup Prompt (Hungarian)
The system uses a specialized Hungarian prompt that:
- Understands Hungarian hyphenation rules
- Recognizes common Hungarian OCR errors
- Preserves Hungarian grammar and syntax
- Handles compound words correctly

### Key Hungarian Features
```python
# Example Hungarian word division handling:
# "szó-\ntag" → "szótag"
# "könyv-\ntár" → "könyvtár"
```

## Dependencies and Imports

### External Libraries
```python
# Core Azure integration
import openai                    # Azure OpenAI SDK
from dotenv import load_dotenv   # Environment management

# EPUB processing
from ebooklib import epub        # EPUB file manipulation
from bs4 import BeautifulSoup   # HTML parsing

# Utilities
import requests                  # HTTP requests
from tqdm import tqdm           # Progress bars
import psutil                   # System monitoring
```

### Standard Library
```python
import os, re, json, time       # Basic utilities
import zipfile, tempfile        # File handling
import shutil                   # File operations
from pathlib import Path        # Path handling
from typing import List, Dict, Tuple, Optional  # Type hints
from dataclasses import dataclass  # Configuration classes
```

## Configuration Management

### Environment Variables
All configuration is managed through environment variables:
- Azure service credentials
- Processing parameters
- Retry and timeout settings
- Token limits and chunking parameters

### Default Values
The system provides sensible defaults for all optional parameters:
- MAX_TOKENS_PER_CHUNK: 3000
- TEMPERATURE: 0.1
- MAX_TOKENS_RESPONSE: 4000
- MAX_RETRIES: 3
- RETRY_DELAY: 2

## Memory Management

### Large File Handling
- **--save-interim flag**: Saves intermediate results to disk
- **Chunked processing**: Processes text in manageable chunks
- **Memory monitoring**: Uses psutil to track memory usage
- **Cleanup**: Removes temporary files and large objects

### Performance Considerations
- Text chunking optimized for Hungarian (1 token ≈ 4 characters)
- Paragraph-first splitting to maintain context
- Progress bars for long operations
- Configurable retry delays to handle rate limits
