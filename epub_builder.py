from ebooklib import epub
import re
from typing import List, Dict, Any

class EPUBBuilder:
    """
    Builds an EPUB file from structured text content.
    """
    def __init__(self):
        self.book = epub.EpubBook()
        self.chapters = []

    def set_metadata(self, title: str, author: str, language: str = 'en', identifier: str = 'unknown'):
        """Sets the EPUB book metadata."""
        self.book.set_identifier(identifier)
        self.book.set_title(title)
        self.book.set_language(language)
        self.book.add_author(author)
        self.language = language # Store language as an instance variable

    def add_chapter(self, title: str, content: str, file_name: str = None):
        """Adds a chapter to the EPUB book."""
        if not file_name:
            # Create a simple file name from the title
            file_name = re.sub(r'[^\w]', '', title).lower() + '.xhtml'
            if not file_name: # Fallback if title is empty or only special chars
                file_name = f'chapter_{len(self.chapters) + 1}.xhtml'

        chapter = epub.EpubHtml(title=title, file_name=file_name, lang=self.language)
        
        # Basic HTML wrapping for the content
        html_content = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
"""
        # Split content into paragraphs and add them
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        for paragraph in paragraphs:
            # Simple heuristic for headings vs paragraphs
            if len(paragraph) < 100 and not paragraph.endswith('.'):
                html_content += f"<h2>{paragraph}</h2>\n"
            else:
                html_content += f"<p>{paragraph}</p>\n"
        
        html_content += """</body>
</html>"""
        
        chapter.content = html_content.encode('utf-8')
        self.book.add_item(chapter)
        self.chapters.append(chapter)

    def build_epub(self, output_path: str):
        """Builds and writes the EPUB file to the specified path."""
        if not self.chapters:
            raise ValueError("No chapters added to the EPUB book.")

        self.book.toc = self.chapters
        self.book.spine = ['nav'] + self.chapters

        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        epub.write_epub(output_path, self.book, {})
        print(f"EPUB file saved to: {output_path}")

if __name__ == "__main__":
    # Example Usage
    builder = EPUBBuilder()
    builder.set_metadata(title="Sample Book", author="John Doe", language="en")

    # Add some chapters
    builder.add_chapter(
        title="Introduction",
        content="""This is the introduction to our sample book.
It explains the purpose and scope of the content.

This is a new paragraph in the introduction.
It demonstrates how paragraphs are handled."""
    )

    builder.add_chapter(
        title="Chapter 1: The Beginning",
        content="""Chapter 1 content starts here.
It's an exciting beginning to our story.

Another paragraph in Chapter 1.
More details and plot points unfold."""
    )
    
    builder.add_chapter(
        title="Chapter 2: The Middle",
        content="""Chapter 2 content.
The story continues to develop.

This is the final paragraph of Chapter 2."""
    )

    output_file = "sample_book.epub"
    builder.build_epub(output_file)
    print(f"Successfully created {output_file}")
