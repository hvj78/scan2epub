# Project Overview

## Purpose

scan2epub is a specialized tool designed to convert scanned or photographed PDF books into clean, reader-optimized EPUB files. The project was created by János Horváth-Varga (hvj78) as a hobby project to address a personal need: his family loves reading on ONYX eBook readers, but many books are not available in clean EPUB format.

## Core Features

### Two-Stage Processing Pipeline

1. **OCR Stage**
   - Extracts text from scanned/photographed PDF books
   - Uses Azure AI Content Understanding service
   - Preserves original document structure (page breaks, line breaks, word divisions)
   - Creates an initial EPUB with raw OCR output

2. **Cleanup Stage**
   - Removes OCR artifacts and formatting issues
   - Uses Azure GPT-4 for intelligent text processing
   - Fixes word divisions and hyphenation errors
   - Optimizes paragraph structure for ebook readers
   - Produces a clean, readable EPUB

### Key Capabilities

- **Preserves book structure** during initial OCR
- **Optimizes for ebook readers** by removing print-specific formatting
- **Azure AI integration** for high-quality OCR and text processing
- **Flexible workflows**: 
  - Direct PDF-to-EPUB conversion
  - Cleanup of existing OCR'd EPUB files
  - OCR-only mode (preserves original layout)
  - Cleanup-only mode (for existing EPUBs)

## Target Audience

- Individuals with scanned book PDFs who want clean EPUBs
- ONYX eBook reader users
- Anyone dealing with poorly formatted OCR'd ebooks
- Hungarian readers (optimized for Hungarian text, but supports other languages)

## Project Background

### Motivation
The project was born from a practical need - the author's family needed a way to convert scanned books into clean EPUB format for their ONYX readers. Many books, especially older or regional publications, are only available as scanned PDFs or poorly formatted EPUBs.

### Development Approach
The project was developed with assistance from:
- Cline plugin for VSCode
- Claude Sonnet 4 (for clever thinking)
- Google Gemini 2.5 Flash (for cost-wise acting in Cline)

### Open Source Philosophy
- Released under MIT License
- Welcomes contributions from the community
- Encourages adaptation and modification
- Only asks for attribution to the original project

## Unique Value Proposition

1. **Specialized for books**: Unlike general OCR tools, this is specifically designed for book conversion
2. **Two-stage approach**: Separates OCR from cleanup, allowing flexibility
3. **AI-powered cleanup**: Uses advanced language models to intelligently fix OCR issues
4. **Hungarian optimization**: Special attention to Hungarian language peculiarities
5. **Reader-focused**: Output is optimized for ebook readers, not just text extraction
