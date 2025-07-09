# Tech Context: scan2epub

## Technology Stack

### Core Language
- **Python 3.8+**: Chosen for its excellent library ecosystem and ease of use
- **Type Hints**: Used throughout for better code clarity

### Key Dependencies

#### Azure Integration
- **openai** (>=1.0.0): Azure OpenAI SDK for GPT-4 integration
- **requests** (>=2.31.0): HTTP client for Azure Content Understanding API

#### EPUB Processing
- **ebooklib** (>=0.18): EPUB file manipulation and creation
- **beautifulsoup4** (>=4.12.0): HTML parsing and manipulation
- **lxml** (>=4.9.0): XML processing backend for BeautifulSoup

#### Utilities
- **python-dotenv** (>=1.0.0): Environment variable management
- **tqdm** (>=4.66.0): Progress bar visualization
- **psutil** (>=5.9.0): System and memory monitoring

## Development Setup

### Environment Configuration
```bash
# 1. Clone repository
git clone https://github.com/hvj78/scan2epub.git
cd scan2epub

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.template .env
# Edit .env with your Azure credentials
```

### Required Environment Variables
```env
# Azure AI Content Understanding
AZURE_CU_API_KEY=your_key_here
AZURE_CU_ENDPOINT=https://your-resource.services.ai.azure.com/

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-gpt4-deployment

# Processing Configuration
MAX_TOKENS_PER_CHUNK=3000
TEMPERATURE=0.1
MAX_TOKENS_RESPONSE=4000
MAX_RETRIES=3
RETRY_DELAY=2
```

## Technical Constraints

### API Limitations
1. **Azure Content Understanding**:
   - Requires publicly accessible URLs
   - File size limits apply
   - Async operation with polling required
   - Rate limits on API calls

2. **Azure OpenAI**:
   - Token limits per request (GPT-4: 8k-32k)
   - Cost per token processed
   - Rate limits (tokens per minute)
   - Regional availability constraints

### Processing Constraints
1. **Memory Usage**:
   - Large EPUBs can exhaust RAM
   - Python's GIL limits parallelization
   - String operations are memory-intensive

2. **Performance**:
   - Network latency for API calls
   - Sequential chunk processing
   - No GPU acceleration used

### Platform Constraints
1. **Operating System**:
   - Tested on Windows, macOS, Linux
   - Path handling differences
   - Character encoding variations

2. **Python Version**:
   - Requires Python 3.8+ for type hints
   - Some libraries may have version conflicts

## Tool Usage Patterns

### Command Line Interface
```bash
# Full pipeline
python scan2epub.py https://example.com/book.pdf output.epub

# OCR only
python scan2epub.py https://example.com/book.pdf output.epub --ocr-only

# Cleanup only
python scan2epub.py input.epub output.epub --cleanup-only

# Debug mode
python scan2epub.py input.pdf output.epub --debug

# Memory-efficient mode
python scan2epub.py large.epub output.epub --cleanup-only --save-interim
```

### Azure Service Patterns

#### Content Understanding API
```python
# Async pattern
POST /contentunderstanding/analyzers/{analyzerId}:analyze
Body: {"url": "https://example.com/document.pdf"}
Response: {"id": "operation-id"}

# Polling pattern
GET /contentunderstanding/analyzerResults/{operationId}
Response: {"status": "Running|Succeeded|Failed", "result": {...}}
```

#### OpenAI API
```python
# Chat completion pattern
client.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": text_chunk}
    ],
    temperature=0.1,
    max_tokens=4000
)
```

## Development Tools

### IDE/Editor Setup
- **VS Code** with Python extension recommended
- **PyCharm** also well-supported
- **.env** file support essential
- **Markdown** preview for documentation

### Testing Tools
- **pytest** for unit testing (future)
- **Manual testing** with sample PDFs
- **Azure Portal** for monitoring API usage
- **EPUB readers** for output validation

### Debugging Tools
- **--debug flag** for verbose output
- **Python debugger** (pdb) compatible
- **Azure logs** for API troubleshooting
- **Memory profiler** for optimization

## Security Considerations

### API Key Management
- Never commit .env file
- Use environment variables only
- Rotate keys regularly
- Monitor usage for anomalies

### Input Validation
- URL validation for PDF input
- File type checking for EPUBs
- Size limits enforcement
- Character encoding validation

### Data Privacy
- No data stored permanently
- Temporary files cleaned up
- Azure data processing policies apply
- User content not logged

## Performance Optimization

### Current Optimizations
- Chunked text processing
- Progress indication
- Configurable retry logic
- Optional disk caching

### Future Optimization Opportunities
- Parallel chunk processing
- Caching of common patterns
- Compression of interim data
- Streaming processing

## Integration Points

### Input Sources
- **Cloud Storage**: Azure Blob, Google Drive, Dropbox
- **Direct URLs**: Any publicly accessible URL
- **Future**: Local file upload support

### Output Targets
- **Local filesystem**: Direct EPUB file creation
- **Future**: Cloud storage integration
- **Future**: Direct e-reader upload

### Monitoring Integration
- **Azure Monitor**: API usage tracking
- **Application Insights**: Performance metrics
- **Cost Management**: Usage alerts
- **Future**: Custom dashboards

## Deployment Considerations

### Local Deployment
- Single user mode
- No concurrency concerns
- Direct file system access
- Simple Python execution

### Future Cloud Deployment
- Containerization needed
- Queue-based processing
- Scalability planning
- Cost optimization

## Maintenance Patterns

### Dependency Updates
```bash
# Check outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package_name

# Update all packages (careful!)
pip install --upgrade -r requirements.txt
```

### Azure API Updates
- Monitor deprecation notices
- Test with new API versions
- Update endpoints as needed
- Maintain backward compatibility

### Code Maintenance
- Regular refactoring
- Documentation updates
- Performance profiling
- Security audits
