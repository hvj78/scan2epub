# Current Limitations & Known Issues

## Major Limitations

### 1. Azure Dependency
- **Complete reliance on Azure services**: Both OCR and cleanup require Azure subscriptions
- **Cost implications**: Processing large books can be expensive
- **Regional availability**: Azure OpenAI has limited regional availability
- **Internet dependency**: Requires stable internet connection for API calls

### 2. PDF Input Constraints
- **Public URL requirement**: PDFs must be accessible via public URL
- **No local file support**: Cannot directly process local PDF files
- **Upload complexity**: Users must handle file uploading to cloud storage
- **URL accessibility**: PDF hosting service must allow Azure to access the file

### 3. Unimplemented Features
- **--preserve-images**: Image preservation not yet implemented
- **--language auto-detection**: Language specification not implemented
- **Local AI support**: No support for local/open-source models
- **Batch processing**: No built-in support for processing multiple files

### 4. Memory and Performance Issues
- **Large file handling**: Memory issues with very large EPUBs
- **Processing time**: Can take 10-30 minutes for large books
- **Single-threaded**: No parallel processing support
- **Memory leaks**: Potential memory issues with very large documents

## Technical Limitations

### OCR Stage Limitations
- **PDF quality dependency**: Poor scans produce poor OCR results
- **Complex layouts**: May struggle with multi-column or complex layouts
- **Image-heavy documents**: Cannot process image-only PDFs effectively
- **Password protection**: Cannot handle password-protected PDFs
- **Large file size limits**: Azure Content Understanding has file size limits

### Cleanup Stage Limitations
- **Hungarian optimization**: Cleanup prompt optimized primarily for Hungarian
- **Context loss**: Text chunking may lose context across chunk boundaries
- **Token limits**: GPT-4 token limits constrain chunk sizes
- **Rate limiting**: Azure API rate limits can slow processing
- **Cost per token**: GPT-4 processing can be expensive for large texts

### EPUB Generation Limitations
- **Simple structure**: Creates basic EPUB structure only
- **No advanced formatting**: Limited support for complex formatting
- **Metadata extraction**: Basic metadata handling from PDFs
- **Chapter detection**: Simple heuristics for chapter identification
- **No table of contents**: Limited TOC generation capabilities

## Known Issues

### Configuration Issues
1. **Environment variable errors**: Common setup problems with .env files
2. **Azure endpoint confusion**: Endpoint URL format issues
3. **API key rotation**: No automatic handling of key rotation
4. **Version compatibility**: API version changes may break functionality

### Processing Issues
1. **Timeout errors**: Long documents may timeout during processing
2. **Encoding problems**: Character encoding issues with some languages
3. **HTML reconstruction**: May lose some formatting during cleanup
4. **Memory exhaustion**: Large EPUBs can exhaust system memory
5. **Incomplete processing**: Some chunks may fail without clear indication

### Output Quality Issues
1. **Over-cleaning**: May remove intentional formatting
2. **Context loss**: Important context may be lost between chunks
3. **Language mixing**: Issues with multi-language documents
4. **Special characters**: Problems with special characters or symbols
5. **Mathematical content**: Poor handling of mathematical formulas

## Workarounds and Mitigation

### For PDF URL Requirement
- Use Azure Blob Storage with SAS tokens
- Use Google Drive with public sharing
- Use GitHub raw file URLs for public documents
- Set up temporary file hosting service

### For Memory Issues
- Use `--save-interim` flag for large files
- Process books in smaller sections
- Increase system RAM
- Close other applications during processing

### For Cost Management
- Use `--ocr-only` mode to test quality first
- Process smaller test sections before full books
- Monitor Azure usage regularly
- Set up cost alerts in Azure Portal

### For Quality Issues
- Review and adjust processing parameters
- Use higher quality source PDFs
- Consider manual post-processing
- Test with different temperature settings

## Platform-Specific Issues

### Windows
- Path handling issues with long filenames
- Character encoding problems in command prompt
- Antivirus interference with temporary files

### macOS/Linux
- Permission issues with temporary directories
- Case-sensitive filesystem issues

## Error Messages and Troubleshooting

### Common Error Messages

1. **"Missing required environment variables"**
   - Cause: .env file not configured properly
   - Solution: Check .env file exists and contains all required variables

2. **"401 Unauthorized"**
   - Cause: Invalid API keys or expired credentials
   - Solution: Verify API keys in Azure portal

3. **"404 Not Found"**
   - Cause: Incorrect endpoint URLs or deployment names
   - Solution: Check endpoint format and deployment names

4. **"Rate limit exceeded"**
   - Cause: Too many API requests
   - Solution: Increase RETRY_DELAY or reduce processing speed

5. **"Memory error" or system freeze**
   - Cause: Large EPUB processing
   - Solution: Use --save-interim flag or increase system memory

### Debug Mode Benefits
Using `--debug` flag provides:
- Detailed processing information
- Memory usage monitoring
- API call logging
- Content preview at each stage
- Error stack traces

## Recommendations for Users

### Before Starting
1. Test with small documents first
2. Verify Azure services are properly configured
3. Ensure stable internet connection
4. Have sufficient system resources available

### During Processing
1. Monitor system resources
2. Don't interrupt long-running processes
3. Check Azure portal for API usage
4. Save interim results for large files

### After Processing
1. Validate output in multiple EPUB readers
2. Compare with original for quality assessment
3. Report issues on GitHub with sample files
4. Consider manual post-processing if needed

## Future Improvement Areas

### High Priority
- Local AI model support
- Direct local file processing
- Better memory management
- Improved error handling

### Medium Priority
- Batch processing capabilities
- Advanced formatting preservation
- Multi-language optimization
- Performance improvements

### Low Priority
- GUI interface
- Cloud deployment options
- Integration with other tools
- Advanced customization options
