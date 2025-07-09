# Product Context: scan2epub

## Why This Project Exists

### The Problem
János Horváth-Varga's family loves reading on their ONYX eBook readers, but many books - especially older Hungarian titles and regional publications - are only available as:
- Scanned PDFs with no text layer
- Poorly OCR'd EPUBs with numerous artifacts
- Physical books that need digitization

Manual cleanup of OCR'd text is tedious and time-consuming, making many books practically unreadable on e-readers.

### The Solution
scan2epub automates the conversion of scanned books into clean, readable EPUBs by:
1. Extracting text from scanned pages using advanced OCR
2. Intelligently cleaning up OCR artifacts using AI
3. Producing properly formatted EPUBs optimized for e-readers

## How It Should Work

### User Journey
1. **User has a scanned PDF book** (uploaded to cloud storage)
2. **User runs scan2epub with the PDF URL**
3. **Tool performs OCR** to extract text
4. **AI cleans up the text** removing artifacts
5. **User receives a clean EPUB** ready for their e-reader

### Key User Experiences

#### For the Casual User
- Simple command-line interface
- Clear progress indicators
- Automatic handling of common issues
- No need to understand technical details

#### For the Power User
- Flexible processing modes (OCR-only, cleanup-only)
- Debug mode for troubleshooting
- Configuration options for optimization
- Memory management for large books

## Product Principles

### 1. Quality Over Speed
- Better to take 30 minutes and produce a readable book
- Preserve the author's intent and book structure
- Don't over-clean and lose important formatting

### 2. Hungarian Language First
- Optimized for Hungarian text peculiarities
- Handles Hungarian hyphenation rules
- Preserves Hungarian-specific characters

### 3. Accessibility
- Works with standard tools (Python, command line)
- Clear documentation and examples
- Helpful error messages
- Open source for community benefit

### 4. Flexibility
- Multiple processing modes for different needs
- Works with both PDFs and existing EPUBs
- Configurable for different quality/speed trade-offs

## User Personas

### Primary: The Family Reader
- **Who**: Author's family members
- **Needs**: Clean EPUBs of Hungarian books
- **Technical Level**: Basic computer skills
- **Pain Points**: Poor quality scans, unreadable EPUBs
- **Success**: Can read favorite books on ONYX reader

### Secondary: The Book Digitizer
- **Who**: People digitizing personal libraries
- **Needs**: Batch conversion capabilities
- **Technical Level**: Comfortable with command line
- **Pain Points**: Time-consuming manual cleanup
- **Success**: Efficiently converts book collections

### Tertiary: The Developer
- **Who**: Contributors and extenders
- **Needs**: Clean, modular code
- **Technical Level**: Python developers
- **Pain Points**: Lack of local AI options
- **Success**: Can contribute improvements

## Success Metrics

### Quality Metrics
- OCR accuracy for Hungarian text
- Artifact removal effectiveness
- Preservation of book structure
- Reader satisfaction

### Performance Metrics
- Processing time per book
- Memory usage efficiency
- API cost per book
- Success rate

### Adoption Metrics
- Number of users
- Books processed
- Community contributions
- Language support expansion

## Future Vision

### Short Term (2025)
- Eliminate Azure dependency with local AI
- Improve memory efficiency
- Add batch processing

### Medium Term (2026-2027)
- Multi-language support
- GUI interface
- Image preservation
- Advanced formatting

### Long Term (2028+)
- Industry-standard tool
- Comprehensive language coverage
- Enterprise features
- Integration ecosystem
