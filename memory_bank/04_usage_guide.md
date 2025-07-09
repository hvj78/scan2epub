# Usage Guide

## Installation

### Prerequisites
- Python 3.8 or higher
- Azure account with required services configured
- Git (for cloning the repository)

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hvj78/scan2epub.git
   cd scan2epub
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.template .env
   # Edit .env with your Azure credentials
   ```

## Command Line Usage

### Basic Syntax
```bash
python scan2epub.py INPUT OUTPUT [OPTIONS]
```

### Arguments
- **INPUT**: 
  - For full pipeline or OCR-only: PDF URL (must be publicly accessible)
  - For cleanup-only: Path to existing EPUB file
- **OUTPUT**: Path where the output EPUB will be saved

### Options
- `--ocr-only`: Run only the OCR stage (PDF to EPUB)
- `--cleanup-only`: Run only the cleanup stage (EPUB to cleaned EPUB)
- `--preserve-images`: Include images in output (not yet implemented)
- `--language LANG`: Set OCR language (not yet implemented, defaults to auto-detect)
- `--debug`: Enable debug output for troubleshooting
- `--save-interim`: Save interim results to disk (reduces memory usage for large files)
- `--help`: Show help message

## Usage Examples

### Full Pipeline (PDF to Clean EPUB)
Convert a scanned PDF from URL to a clean, optimized EPUB:
```bash
python scan2epub.py https://example.com/scanned_book.pdf clean_book.epub
```

This will:
1. Download and OCR the PDF using Azure Content Understanding
2. Create an interim EPUB with raw OCR text
3. Clean up the text using Azure GPT-4
4. Output a reader-optimized EPUB

### OCR Only Mode
Extract text from PDF without cleanup:
```bash
python scan2epub.py https://example.com/book.pdf raw_ocr.epub --ocr-only
```

Use this when:
- You want to preserve the original formatting
- The OCR quality is already good
- You plan to do manual editing

### Cleanup Only Mode
Clean an existing OCR'd EPUB:
```bash
python scan2epub.py messy_ocr.epub clean_book.epub --cleanup-only
```

Use this when:
- You have an EPUB with OCR artifacts
- You downloaded a poorly formatted EPUB
- You want to optimize an existing EPUB for reading

### Debug Mode
Enable detailed logging:
```bash
python scan2epub.py input.pdf output.epub --debug
```

### Memory-Efficient Processing
For large books that might cause memory issues:
```bash
python scan2epub.py large_book.epub cleaned.epub --cleanup-only --save-interim
```

## Input Requirements

### PDF Requirements (for OCR)
- Must be accessible via public URL
- Should be a scanned or photographed book
- Best results with clear, high-resolution scans
- Any language supported by Azure Content Understanding

### EPUB Requirements (for cleanup)
- Standard EPUB format (EPUB 2 or 3)
- Text-based content (not image-only EPUBs)
- Any language, but optimized for Hungarian

## Output Details

### File Naming
- Default adds "_cleaned" suffix for cleanup operations
- Backup files created with ".backup" extension
- Interim files (if --save-interim) stored in temp directory

### EPUB Structure
The output EPUB will have:
- Clean, properly formatted HTML chapters
- Preserved metadata (title, author, language)
- Optimized paragraph structure
- Removed OCR artifacts
- Fixed word hyphenation

## Workflow Recommendations

### For Scanned PDFs
1. Upload PDF to cloud storage (Azure Blob, Google Drive, etc.)
2. Get a public URL for the PDF
3. Run full pipeline: `python scan2epub.py [URL] output.epub`
4. Review the output and adjust if needed

### For Existing EPUBs
1. Test with a small section first
2. Use --debug flag to identify issues
3. Run cleanup: `python scan2epub.py input.epub output.epub --cleanup-only`
4. Compare before/after to ensure quality

### For Large Books
1. Use --save-interim flag to prevent memory issues
2. Monitor system resources during processing
3. Consider processing in sections if needed
4. Allow extra time for processing (can take 10-30 minutes)

## Best Practices

### Quality Optimization
1. **Source Quality**: Use highest resolution scans available
2. **Language Setting**: Specify language when known (future feature)
3. **Testing**: Always test with a few pages first
4. **Validation**: Open output in multiple EPUB readers to verify

### Performance Tips
1. **Network**: Ensure stable internet connection for API calls
2. **Batch Processing**: Process multiple books sequentially, not in parallel
3. **Error Handling**: Check logs if processing fails
4. **Resource Management**: Close other applications for large books

### Cost Management
1. **Preview First**: Use --ocr-only to check OCR quality before cleanup
2. **Small Tests**: Start with short documents to verify setup
3. **Monitor Usage**: Check Azure portal for API usage
4. **Optimize Chunks**: Adjust MAX_TOKENS_PER_CHUNK if needed

## Common Use Cases

### Academic Texts
- Often have complex formatting
- May need manual review after processing
- Consider --ocr-only mode for preserving citations

### Fiction Books
- Usually process well with default settings
- Focus on readability over formatting
- Full pipeline recommended

### Historical Documents
- May have degraded scan quality
- Might require multiple processing attempts
- Consider adjusting temperature for better results

### Multi-Language Books
- Azure Content Understanding handles most languages
- Cleanup prompt is optimized for Hungarian
- May need prompt customization for other languages

## Troubleshooting Tips

### If OCR fails:
- Verify PDF URL is publicly accessible
- Check Azure Content Understanding service status
- Ensure PDF is not password-protected
- Try a different PDF hosting service

### If cleanup fails:
- Check GPT-4 deployment is active
- Verify token limits aren't exceeded
- Use --debug flag for detailed errors
- Try --save-interim for memory issues

### If output is poor:
- Review source PDF quality
- Adjust processing parameters in .env
- Consider manual post-processing
- Report issues on GitHub
