# scan2epub

Convert scanned or photographed pdf books to clean, reader-optimized EPUB files using Azure AI for OCR and GPT for making the layout ebook reader friendly.

## Features

- **Two-stage processing pipeline**:
  1. **OCR Stage**: Extract text from scanned/photographed PDF books using Azure AI Content Understanding service while preserving original structure (page breaks, line breaks, word divisions)
  2. **Cleanup Stage**: Remove OCR artifacts and optimize layout for ebook readers using Azure GPT, creating a clean reading experience

- **Local PDF file support** (NEW!): Process PDF files directly from your computer without manual upload
- **Preserves book structure** during initial OCR
- **Optimizes for ebook readers** by removing print-specific formatting
- **Azure AI integration** for high-quality OCR and text processing
- **Supports both workflows**: Direct PDF-to-EPUB conversion or cleanup of existing OCR'd EPUB files
- **Configurable settings** via INI file for easy customization

## Prerequisites

- Python 3.8 or higher
- Azure AI account with access to:
  - Azure AI Document Intelligence (for OCR)
  - Azure OpenAI/GPT service (for cleanup)
  - Azure Blob Storage (for local PDF file support)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scan2epub.git
cd scan2epub
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Azure credentials in a .env file:
- copy .env.template .env
- add your API keys and Azure AI service parameters to the .env file, follow the comments in the file!

## Configuration

The tool can be configured using the `scan2epub.ini` file. A default configuration file is created automatically on first run.

### Configuration Options

```ini
[Storage]
max_file_size_mb = 256        # Maximum size for local PDF uploads
blob_container_name = scan2epub-temp  # Azure container name
sas_token_expiry_hours = 1    # URL expiration time

[Processing]
debug = false                 # Enable debug output
save_interim = false          # Save interim results to disk

[Cleanup]
cleanup_on_failure = true     # Clean up Azure files even on failure
log_cleanup = true            # Log cleanup operations
```

For detailed configuration and local PDF support documentation, see [docs/local-pdf-support.md](docs/local-pdf-support.md).

## Usage

### Basic Usage

Convert a scanned PDF book to EPUB:
```bash
# From a local PDF file (NEW!)
python scan2epub.py my_book.pdf output.epub

# From a publicly accessible URL
python scan2epub.py https://example.com/input.pdf output.epub
```

### Advanced Usage

Run only the OCR stage (to keep the original structure, layout, typesetting of the book):
```bash
python scan2epub.py https://example.com/input.pdf output.epub --ocr-only
```

Run only the cleanup stage on an existing OCR'd EPUB you have found on internet:
```bash
python scan2epub.py input.epub output.epub --cleanup-only
```

### Command Line Options

```
python scan2epub.py INPUT OUTPUT [OPTIONS]

Arguments:
  INPUT   Input file (PDF file or URL for OCR, EPUB for cleanup only)
  OUTPUT  Output EPUB file path

Options:
  --ocr-only        Run only the OCR stage
  --cleanup-only    Run only the cleanup stage
  --preserve-images Include images in the output EPUB (not yet implemented)
  --language LANG   Set OCR language (default: Hungarian)
  --debug           Enable debug output
  --save-interim    Save interim results to disk (reduces memory usage)
  --config PATH     Path to configuration file (default: scan2epub.ini)
  --help            Show this help message
```

## How It Works

### Stage 1: OCR Processing
- Accepts both local PDF files and publicly accessible URLs
- For local files: automatically uploads to temporary Azure Blob Storage
- Uses Azure AI Content Understanding to extract text from scanned/photographed PDF pages
- Maintains original document structure (paragraphs, line breaks, page breaks)
- Preserves word divisions and hyphenation from the original text
- Creates an initial EPUB with raw OCR output
- Automatically cleans up temporary files after processing

### Stage 2: Cleanup Processing
- Uses Azure GPT to analyze and clean OCR artifacts
- Removes unnecessary page breaks and line breaks
- Fixes word divisions and hyphenation errors
- Optimizes paragraph structure for ebook readers
- Produces a clean, readable EPUB optimized for digital reading

## Examples

### Converting a local scanned book:
```bash
python scan2epub.py my_scanned_book.pdf clean_book.epub
```

### Converting a scanned academic book (from URL):
```bash
python scan2epub.py https://example.com/scanned_textbook.pdf clean_textbook.epub
```

### Cleaning up an existing OCR'd file:
```bash
python scan2epub.py messy_ocr.epub clean_book.epub --cleanup-only
```

### Processing with custom configuration:
```bash
python scan2epub.py --config my_settings.ini --debug book.pdf output.epub
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You can freely do whatever you want with this codebase, just add a note that the origin is:

[scan2epub](https://github.com/hvj78/scan2epub) by János Horváth-Varga aka [hvj78](https://github.com/hvj78)

## Acknowledgments

- Azure AI Content Understanding service for OCR capabilities
- Azure OpenAI for text processing and cleanup
- The open source community for EPUB processing libraries
- The Cline plugin for VSCode made it possible — without it, I wouldn’t have had time to write the code line by line.
- Claude Sonnet 4 and Google Gemini 2.5 Flash models for clever thinking and cost-wise acting in Cline

## Support

If you encounter any issues or have questions:
- Check the [Issues](https://github.com/hvj78/scan2epub/issues) page
- Create a new issue if your problem isn't already reported
- Provide sample files and error messages when reporting bugs

Please note, that this is a hobby project for me, as my family loves reading and we have many ONYX eBook readers, but several books are unavailable in a clean ePub format, so this is why I decided to create this little python tool.

## Roadmap

I would like to implement a non-Azure dependent version later, where you would be able to use the project with open source visual language models (VLMs) to do the OCR and also open source large language models (LLMs) to clean up the layout after the OCR phase. These open source models can be run on a regular (preferrably stronger) PC/Mac, but as we speak Hungarian and our language is not yet supported very well with these smaller, open soure models, I decided to start using Azure AI with first version: supporting the most languages with very high quality.

You are absolutely welcomed to add this local AI capability to this project, send me pull requests please!

---

**Note**: This tool requires Azure AI services for now. Make sure you have appropriate usage limits and understand the associated costs before processing large volumes of books!
