# Project Brief: scan2epub

## Project Overview
scan2epub is a Python-based tool that converts scanned or photographed PDF books into clean, reader-optimized EPUB files using Azure AI services.

## Core Requirements

### Functional Requirements
1. **PDF to EPUB Conversion**: Accept scanned PDF books (via URL) and convert them to EPUB format
2. **OCR Processing**: Extract text from scanned pages using Azure AI Content Understanding
3. **Text Cleanup**: Remove OCR artifacts and optimize text for ebook readers using Azure GPT-4
4. **Flexible Processing Modes**:
   - Full pipeline (PDF → OCR → Cleanup → EPUB)
   - OCR-only mode (PDF → EPUB with raw OCR)
   - Cleanup-only mode (EPUB → Cleaned EPUB)

### Non-Functional Requirements
1. **Language Support**: Optimized for Hungarian text processing
2. **Memory Management**: Handle large books without exhausting system memory
3. **Error Handling**: Graceful degradation and clear error messages
4. **Progress Tracking**: Visual feedback during long operations

## Project Goals

### Primary Goals
1. Enable family members to read scanned books on ONYX eBook readers
2. Produce clean, readable EPUBs from poor-quality scans
3. Automate the tedious process of manual OCR cleanup

### Secondary Goals
1. Support multiple languages beyond Hungarian
2. Eliminate dependency on expensive Azure services
3. Create a tool useful for the broader community

## Project Scope

### In Scope
- OCR processing of scanned PDFs
- AI-powered text cleanup
- EPUB generation with proper formatting
- Command-line interface
- Azure service integration

### Out of Scope (Current Version)
- GUI interface
- Local AI model support
- Direct local file processing (requires URL)
- Image preservation in EPUBs
- Batch processing

## Success Criteria
1. Successfully converts scanned Hungarian books to readable EPUBs
2. Removes common OCR artifacts (hyphenation, line breaks, page numbers)
3. Preserves book structure and readability
4. Processes books within reasonable time (10-30 minutes)
5. Provides clear feedback and error handling

## Constraints
1. **Technical**: Requires Azure AI services (Content Understanding + OpenAI)
2. **Financial**: Azure API costs for processing
3. **Input**: PDFs must be publicly accessible via URL
4. **Performance**: Memory limitations for very large books
5. **Language**: Cleanup optimization primarily for Hungarian

## Target Users
1. **Primary**: Author's family members with ONYX eBook readers
2. **Secondary**: Hungarian readers needing clean EPUBs
3. **Tertiary**: Anyone dealing with poorly OCR'd ebooks

## Project Timeline
- **Current Status**: v1.0 - Functional with Azure dependency
- **Next Major Milestone**: Local AI support to eliminate cloud dependency
- **Long-term Vision**: Comprehensive, multi-language, open-source solution
