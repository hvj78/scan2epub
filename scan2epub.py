#!/usr/bin/env python3
"""
EPUB OCR Cleanup Script with Azure GPT-4.1 Integration

This script cleans up OCR artifacts from EPUB files using Azure OpenAI GPT-4.1.
It removes page separations, line breaks, word divisions, and combines Hungarian
divided words while preserving the original content and meaning.

Author: Generated for Hungarian EPUB cleanup
"""

import os
import re
import json
import time
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Third-party imports
import openai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from ebooklib import epub
from tqdm import tqdm

# Local imports
from pdf_ocr_processor import PDFOCRProcessor
from epub_builder import EPUBBuilder

# Load environment variables
load_dotenv()

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

class EPUBOCRCleaner:
    """Main class for cleaning OCR artifacts from EPUB files using Azure GPT-4.1"""
    
    def __init__(self):
        self.config = self._load_azure_config()
        self.client = self._initialize_azure_client()
        
    def _load_azure_config(self) -> AzureConfig:
        """Load Azure OpenAI configuration from environment variables"""
        required_vars = [
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT', 
            'AZURE_OPENAI_API_VERSION',
            'AZURE_OPENAI_DEPLOYMENT_NAME'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
            
        return AzureConfig(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            max_tokens_per_chunk=int(os.getenv('MAX_TOKENS_PER_CHUNK', 3000)),
            temperature=float(os.getenv('TEMPERATURE', 0.1)),
            max_tokens_response=int(os.getenv('MAX_TOKENS_RESPONSE', 4000)),
            max_retries=int(os.getenv('MAX_RETRIES', 3)),
            retry_delay=int(os.getenv('RETRY_DELAY', 2))
        )
    
    def _initialize_azure_client(self) -> openai.AzureOpenAI:
        """Initialize Azure OpenAI client"""
        return openai.AzureOpenAI(
            api_key=self.config.api_key,
            api_version=self.config.api_version,
            azure_endpoint=self.config.endpoint
        )
    
    def extract_epub_content(self, epub_path: str) -> Tuple[Dict, str]:
        """Extract content from EPUB file"""
        print(f"Extracting EPUB content from: {epub_path}")
        
        # Create temporary directory for extraction
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Extract EPUB (which is a ZIP file)
            with zipfile.ZipFile(epub_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read the EPUB using ebooklib
            book = epub.read_epub(epub_path)
            
            # Extract text content from all items
            content_items = []
            for item in book.get_items():
                if item.get_type() == 9:  # EBOOKLIB_ITEM_DOCUMENT
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text_content = soup.get_text()
                    
                    content_items.append({
                        'id': item.get_id(),
                        'file_name': item.get_name(),
                        'title': getattr(item, 'title', ''),
                        'content': text_content,
                        'html_content': item.get_content().decode('utf-8')
                    })
            
            metadata = {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
                'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown',
                'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'hu',
                'identifier': book.get_metadata('DC', 'identifier')[0][0] if book.get_metadata('DC', 'identifier') else 'unknown'
            }
            
            return {'content_items': content_items, 'metadata': metadata}, temp_dir
            
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Error extracting EPUB: {str(e)}")
    
    def analyze_ocr_artifacts(self, text: str) -> Dict[str, int]:
        """Analyze text for common OCR artifacts"""
        artifacts = {
            'excessive_line_breaks': len(re.findall(r'\n\s*\n\s*\n', text)),
            'hyphenated_words': len(re.findall(r'\w+-\s*\n\s*\w+', text)),
            'single_line_paragraphs': len(re.findall(r'\n\s*\S[^\n]*\n\s*\n', text)),
            'page_numbers': len(re.findall(r'\n\s*\d+\s*\n', text)),
            'short_lines': len([line for line in text.split('\n') if 0 < len(line.strip()) < 30])
        }
        return artifacts
    
    def create_cleanup_prompt(self) -> str:
        """Create the prompt for LLM-based OCR cleanup"""
        return """Te egy magyar nyelvű szöveg OCR hibáinak javítására specializálódott asszisztens vagy. 

FELADATOD:
1. Távolítsd el az OCR által okozott felesleges sortöréseket és oldalelválasztásokat
2. Egyesítsd a sorvégeken elválasztott magyar szavakat (pl. "szó-\ntag" → "szótag")
3. Távolítsd el a felesleges szóközöket és formázási hibákat
4. Őrizd meg a bekezdések természetes szerkezetét
5. NE változtasd meg a szöveg jelentését vagy tartalmát

FONTOS SZABÁLYOK:
- Csak az OCR hibákat javítsd, a tartalmat ne módosítsd
- A magyar nyelvtan szabályait kövesd a szóegyesítésnél
- Őrizd meg a fejezetek és bekezdések logikus felépítését
- Ha bizonytalan vagy, inkább hagyd változatlanul

Kérlek, tisztítsd meg a következő szöveget:

"""
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks suitable for LLM processing"""
        # Rough estimation: 1 token ≈ 4 characters for Hungarian text
        max_chars = self.config.max_tokens_per_chunk * 2
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit
            if len(current_chunk) + len(paragraph) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraph is too long, split by sentences
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > max_chars:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Even single sentence is too long, force split
                                chunks.append(sentence[:max_chars])
                                current_chunk = sentence[max_chars:]
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def clean_text_with_llm(self, text: str) -> str:
        """Clean text using Azure GPT-4.1"""
        chunks = self.chunk_text(text)
        cleaned_chunks = []
        
        print(f"Processing {len(chunks)} text chunks...")
        
        for i, chunk in enumerate(tqdm(chunks, desc="Cleaning text")):
            for attempt in range(self.config.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.config.deployment_name,
                        messages=[
                            {"role": "system", "content": self.create_cleanup_prompt()},
                            {"role": "user", "content": chunk}
                        ],
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens_response
                    )
                    
                    cleaned_text = response.choices[0].message.content.strip()
                    cleaned_chunks.append(cleaned_text)
                    break
                    
                except Exception as e:
                    print(f"Error processing chunk {i+1}, attempt {attempt+1}: {str(e)}")
                    if attempt == self.config.max_retries - 1:
                        print(f"Failed to process chunk {i+1}, using original text")
                        cleaned_chunks.append(chunk)
                    else:
                        time.sleep(self.config.retry_delay)
        
        return "\n\n".join(cleaned_chunks)
    
    def reconstruct_html(self, cleaned_text: str, original_html: str) -> str:
        """Reconstruct HTML structure with cleaned text"""
        # If cleaned text is empty, return a minimal HTML structure
        if not cleaned_text.strip():
            return """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Empty Chapter</title></head>
<body><p>This chapter appears to be empty.</p></body>
</html>"""
        
        # Create a simple, clean HTML structure
        # Split cleaned text into paragraphs
        paragraphs = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]
        
        # If no paragraphs found, treat the whole text as one paragraph
        if not paragraphs:
            paragraphs = [cleaned_text.strip()]
        
        # Create a simple HTML structure
        html_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter</title></head>
<body>
"""
        
        # Add paragraphs
        for paragraph in paragraphs:
            if paragraph.strip():
                # Check if this looks like a heading
                if len(paragraph) < 100 and not paragraph.endswith('.'):
                    html_content += f"<h2>{paragraph}</h2>\n"
                else:
                    html_content += f"<p>{paragraph}</p>\n"
        
        html_content += """</body>
</html>"""
        
        return html_content
    
    def create_cleaned_epub(self, original_data: Dict, cleaned_content: List[Dict], output_path: str, debug: bool = False):
        """Create a new EPUB with cleaned content"""
        print("Creating cleaned EPUB...")
        
        # Check if we have any content to work with
        if not cleaned_content:
            raise ValueError("No content found to create EPUB. All chapters appear to be empty.")
        
        if debug:
            print(f"🔍 DEBUG: Starting EPUB creation with {len(cleaned_content)} chapters")
        
        # Create new book
        book = epub.EpubBook()
        
        # Set metadata
        metadata = original_data['metadata']
        book.set_identifier(metadata['identifier'])
        book.set_title(f"{metadata['title']} (Cleaned)")
        book.set_language(metadata['language'])
        book.add_author(metadata['author'])
        
        if debug:
            print(f"🔍 DEBUG: Set metadata - Title: {metadata['title']}, Language: {metadata['language']}")
        
        # Add cleaned content items
        chapters = []
        for i, item_data in enumerate(cleaned_content):
            if debug:
                print(f"🔍 DEBUG: Processing chapter {i+1}: {item_data['file_name']}")
            
            # Ensure we have valid HTML content
            html_content = item_data.get('cleaned_html', '')
            if not html_content.strip():
                if debug:
                    print(f"🔍 DEBUG: Empty HTML content for {item_data['file_name']}, creating placeholder")
                # Create minimal content if empty
                html_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Empty Chapter</title></head>
<body><p>This chapter appears to be empty.</p></body>
</html>"""
            
            if debug:
                print(f"🔍 DEBUG: HTML content length: {len(html_content)} chars")
                print(f"🔍 DEBUG: HTML content sample: {repr(html_content[:150])}")
            
            # Create chapter
            chapter = epub.EpubHtml(
                title=item_data.get('title', f'Chapter {i+1}'),
                file_name=item_data['file_name'],
                lang=metadata['language']
            )
            
            # Set content as bytes to ensure proper encoding
            try:
                if isinstance(html_content, str):
                    chapter.content = html_content.encode('utf-8')
                else:
                    chapter.content = html_content
                
                if debug:
                    print(f"🔍 DEBUG: Set content for {item_data['file_name']} - Content type: {type(chapter.content)}, Length: {len(chapter.content)}")
                
                # Verify content was set
                if hasattr(chapter, 'content') and chapter.content:
                    if debug:
                        print(f"🔍 DEBUG: Content verification passed for {item_data['file_name']}")
                else:
                    if debug:
                        print(f"🔍 DEBUG: WARNING - Content verification failed for {item_data['file_name']}")
                
            except Exception as e:
                print(f"❌ Error setting content for {item_data['file_name']}: {str(e)}")
                if debug:
                    print(f"🔍 DEBUG: Falling back to simple string assignment")
                chapter.content = html_content
            
            book.add_item(chapter)
            chapters.append(chapter)
            
            if debug:
                print(f"🔍 DEBUG: Added chapter {i+1} to book")
        
        # Ensure we have at least one chapter
        if not chapters:
            if debug:
                print(f"🔍 DEBUG: No chapters found, creating placeholder")
            # Create a placeholder chapter
            placeholder_chapter = epub.EpubHtml(
                title='Placeholder Chapter',
                file_name='placeholder.xhtml',
                lang=metadata['language']
            )
            placeholder_content = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Placeholder</title></head>
<body><p>This EPUB was processed but no readable content was found.</p></body>
</html>"""
            placeholder_chapter.content = placeholder_content.encode('utf-8')
            book.add_item(placeholder_chapter)
            chapters.append(placeholder_chapter)
        
        if debug:
            print(f"🔍 DEBUG: Total chapters to include: {len(chapters)}")
        
        # Define table of contents and spine
        book.toc = chapters
        book.spine = ['nav'] + chapters
        
        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        if debug:
            print(f"🔍 DEBUG: Added navigation files, about to write EPUB")
        
        # Write the EPUB
        try:
            epub.write_epub(output_path, book, {})
            print(f"Cleaned EPUB saved to: {output_path}")
            
            if debug:
                # Verify the created EPUB
                import os
                file_size = os.path.getsize(output_path)
                print(f"🔍 DEBUG: Created EPUB file size: {file_size} bytes")
                
                # Try to read it back to verify
                try:
                    test_book = epub.read_epub(output_path)
                    test_items = list(test_book.get_items())
                    print(f"🔍 DEBUG: Verification - EPUB contains {len(test_items)} items")
                    
                    for item in test_items:
                        if item.get_type() == 9:  # EBOOKLIB_ITEM_DOCUMENT
                            content_length = len(item.get_content()) if item.get_content() else 0
                            print(f"🔍 DEBUG: Verification - {item.get_name()}: {content_length} bytes")
                            
                except Exception as verify_error:
                    print(f"🔍 DEBUG: Verification failed: {str(verify_error)}")
                    
        except Exception as e:
            print(f"❌ Error writing EPUB: {str(e)}")
            raise
    
    def clean_epub(self, input_path: str, output_path: str = None, debug: bool = False, save_interim: bool = False):
        """Main method to clean an EPUB file"""
        if not output_path:
            base_name = Path(input_path).stem
            output_path = f"{base_name}_cleaned.epub"
        
        print(f"Starting EPUB cleanup: {input_path}")
        print(f"Output will be saved to: {output_path}")
        
        # Create backup
        backup_path = f"{input_path}.backup"
        if not os.path.exists(backup_path):
            shutil.copy2(input_path, backup_path)
            print(f"Backup created: {backup_path}")
        
        # Create interim directory if saving to disk
        interim_dir = None
        if save_interim:
            interim_dir = tempfile.mkdtemp(prefix="epub_cleanup_")
            print(f"Interim results will be saved to: {interim_dir}")
        
        try:
            # Extract content
            original_data, temp_dir = self.extract_epub_content(input_path)
            
            if debug:
                print(f"\n🔍 DEBUG: Found {len(original_data['content_items'])} content items")
                for i, item in enumerate(original_data['content_items']):
                    print(f"  Item {i+1}: {item['file_name']} - Content length: {len(item['content'])} chars")
                
                # Memory usage monitoring
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                print(f"🔍 DEBUG: Current memory usage: {memory_mb:.1f} MB")
            
            # Process each content item
            cleaned_content = []
            total_artifacts = 0
            
            for item in original_data['content_items']:
                # Skip navigation files and other special files
                if item['file_name'] in ['nav.xhtml', 'toc.ncx', 'content.opf'] or 'nav' in item['file_name'].lower():
                    if debug:
                        print(f"🔍 DEBUG: Skipping navigation file: {item['file_name']}")
                    continue
                
                if item['content'].strip():  # Only process items with content
                    print(f"\nProcessing: {item['file_name']}")
                    
                    # Analyze artifacts
                    artifacts = self.analyze_ocr_artifacts(item['content'])
                    total_artifacts += sum(artifacts.values())
                    print(f"Found artifacts: {artifacts}")
                    
                    if debug:
                        print(f"🔍 DEBUG: Original content preview (first 200 chars):")
                        print(f"  {repr(item['content'][:200])}")
                    
                    # Clean text with LLM
                    cleaned_text = self.clean_text_with_llm(item['content'])
                    
                    if debug:
                        print(f"🔍 DEBUG: Cleaned text preview (first 200 chars):")
                        print(f"  {repr(cleaned_text[:200])}")
                    
                    # Reconstruct HTML
                    cleaned_html = self.reconstruct_html(cleaned_text, item['html_content'])
                    
                    if debug:
                        print(f"🔍 DEBUG: HTML content preview (first 300 chars):")
                        print(f"  {repr(cleaned_html[:300])}")
                    
                    # Save interim results to disk if requested
                    if save_interim and interim_dir:
                        interim_file = os.path.join(interim_dir, f"{item['file_name']}.json")
                        interim_data = {
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'original_content': item['content'],
                            'cleaned_text': cleaned_text,
                            'cleaned_html': cleaned_html,
                            'artifacts': artifacts
                        }
                        with open(interim_file, 'w', encoding='utf-8') as f:
                            json.dump(interim_data, f, ensure_ascii=False, indent=2)
                        
                        if debug:
                            print(f"🔍 DEBUG: Saved interim results to: {interim_file}")
                        
                        # Store only essential data in memory
                        cleaned_content.append({
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'cleaned_html': cleaned_html
                        })
                        
                        # Monitor memory usage after each chapter
                        if debug:
                            memory_mb = process.memory_info().rss / 1024 / 1024
                            print(f"🔍 DEBUG: Memory usage after processing: {memory_mb:.1f} MB")
                    else:
                        # Store everything in memory (original behavior)
                        cleaned_content.append({
                            'file_name': item['file_name'],
                            'title': item['title'],
                            'cleaned_html': cleaned_html
                        })
                else:
                    if debug:
                        print(f"🔍 DEBUG: Skipping empty item: {item['file_name']}")
            
            if debug:
                print(f"\n🔍 DEBUG: Final cleaned_content has {len(cleaned_content)} items")
                for i, item in enumerate(cleaned_content):
                    print(f"  Item {i+1}: {item['file_name']} - HTML length: {len(item['cleaned_html'])} chars")
            
            # Create new EPUB
            self.create_cleaned_epub(original_data, cleaned_content, output_path, debug=debug)
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            print(f"\n✅ EPUB cleanup completed!")
            print(f"📊 Total OCR artifacts found: {total_artifacts}")
            print(f"📁 Original file: {input_path}")
            print(f"📁 Cleaned file: {output_path}")
            print(f"📁 Backup file: {backup_path}")
            
        except Exception as e:
            print(f"❌ Error during cleanup: {str(e)}")
            raise


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert scanned PDFs to clean EPUBs or clean existing EPUBs using Azure AI.'
    )
    parser.add_argument('input_file', help='Path to input file (PDF URL for OCR, EPUB for cleanup)')
    parser.add_argument('output_file', help='Path to output EPUB file')
    parser.add_argument('--ocr-only', action='store_true', 
                        help='Run only the OCR stage (PDF to EPUB conversion)')
    parser.add_argument('--cleanup-only', action='store_true', 
                        help='Run only the cleanup stage (EPUB to cleaned EPUB)')
    parser.add_argument('--preserve-images', action='store_true', 
                        help='(Not yet implemented) Include images in the output EPUB during OCR stage')
    parser.add_argument('--language', type=str, default='auto', 
                        help='(Not yet implemented) Set OCR language (default: auto-detect)')
    parser.add_argument('--debug', action='store_true', 
                        help='Enable debug output to troubleshoot issues')
    parser.add_argument('--save-interim', action='store_true', 
                        help='Save interim results to disk to reduce memory usage (for cleanup stage)')
    
    args = parser.parse_args()

    input_ext = Path(args.input_file).suffix.lower()
    output_ext = Path(args.output_file).suffix.lower()

    if output_ext != '.epub':
        print(f"Error: Output file must have .epub extension, but got {output_ext}")
        return 1

    if args.ocr_only and args.cleanup_only:
        print("Error: Cannot use --ocr-only and --cleanup-only simultaneously.")
        return 1

    try:
        if args.ocr_only:
            if input_ext != '.pdf':
                print("Error: --ocr-only mode requires a PDF input file.")
                return 1
            
            print(f"Running OCR only: {args.input_file} (URL) -> {args.output_file}")
            pdf_processor = PDFOCRProcessor()
            # The input_file is now expected to be a URL for PDF processing
            ocr_result = pdf_processor.process_pdf(args.input_file)
            extracted_text = pdf_processor.extract_text_from_ocr_result(ocr_result)

            # Basic metadata extraction from PDF (can be enhanced)
            title = Path(args.input_file).stem
            author = "Unknown" # Placeholder, can be extracted from PDF metadata
            language = args.language if args.language != 'auto' else 'en' # Default to English if auto-detect not implemented

            epub_builder = EPUBBuilder()
            epub_builder.set_metadata(title=title, author=author, language=language)
            epub_builder.add_chapter(title="Document Content", content=extracted_text)
            epub_builder.build_epub(args.output_file)
            
            print(f"OCR to EPUB conversion completed: {args.input_file} -> {args.output_file}")

        elif args.cleanup_only:
            if input_ext != '.epub':
                print("Error: --cleanup-only mode requires an EPUB input file.")
                return 1
            
            print(f"Running EPUB cleanup only: {args.input_file} -> {args.output_file}")
            cleaner = EPUBOCRCleaner()
            cleaner.clean_epub(args.input_file, args.output_file, debug=args.debug, save_interim=args.save_interim)
            
        else: # Full pipeline: PDF -> OCR -> EPUB -> Cleanup
            if input_ext != '.pdf':
                print("Error: Full pipeline requires a PDF input file.")
                return 1
            
            print(f"Running full pipeline: {args.input_file} (URL) -> {args.output_file}")
            
            # Step 1: OCR PDF and convert to interim EPUB
            interim_epub_path = Path(args.output_file).with_stem(Path(args.output_file).stem + "_interim_ocr").with_suffix(".epub")
            
            print(f"Step 1/2: Performing OCR on PDF (from URL) and creating interim EPUB: {interim_epub_path}")
            pdf_processor = PDFOCRProcessor()
            # The input_file is now expected to be a URL for PDF processing
            ocr_result = pdf_processor.process_pdf(args.input_file)
            extracted_text = pdf_processor.extract_text_from_ocr_result(ocr_result)

            # Basic metadata extraction from PDF (can be enhanced)
            title = Path(args.input_file).stem
            author = "Unknown" # Placeholder, can be extracted from PDF metadata
            language = args.language if args.language != 'auto' else 'en' # Default to English if auto-detect not implemented

            epub_builder = EPUBBuilder()
            epub_builder.set_metadata(title=title, author=author, language=language)
            epub_builder.add_chapter(title="Document Content", content=extracted_text)
            epub_builder.build_epub(interim_epub_path)
            
            print(f"Interim EPUB created: {interim_epub_path}")

            # Step 2: Clean up the interim EPUB
            print(f"Step 2/2: Cleaning up interim EPUB: {interim_epub_path} -> {args.output_file}")
            cleaner = EPUBOCRCleaner()
            cleaner.clean_epub(interim_epub_path, args.output_file, debug=args.debug, save_interim=args.save_interim)
            
            # Clean up interim file
            os.remove(interim_epub_path)
            print(f"Cleaned up interim file: {interim_epub_path}")
            
            print(f"Full pipeline completed: {args.input_file} -> {args.output_file}")

        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
