import json
from pathlib import Path

import pytest
from ebooklib import epub

from scan2epub.epub.translator import EPUBTranslator
from scan2epub.translate.translator import ITranslator
from scan2epub.utils.errors import TranslationError


def _make_minimal_epub(epub_path: Path, paragraphs):
    """
    Create a minimal EPUB with a single chapter whose text contains explicit blank-line
    separated paragraphs via a <pre> block to ensure BeautifulSoup.get_text preserves newlines.
    """
    book = epub.EpubBook()
    book.set_identifier("test-id")
    book.set_title("Test Book")
    book.set_language("hu")
    book.add_author("Tester")

    # Use a pre block to preserve newlines in extracted text
    text = "\n\n".join(paragraphs)
    html = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body><pre>{text}</pre></body>
</html>"""

    ch = epub.EpubHtml(title="Chapter 1", file_name="ch1.xhtml", lang="hu")
    ch.content = html.encode("utf-8")
    book.add_item(ch)

    # Navigation
    book.toc = [ch]
    book.spine = ["nav", ch]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(epub_path), book, {})


class EchoTranslator(ITranslator):
    """Returns the same text (no-op)."""
    def translate_text(self, segments, to_lang, from_lang=None):
        return list(segments)


class OneChangeTranslator(ITranslator):
    """Changes only the first paragraph by appending a marker."""
    def translate_text(self, segments, to_lang, from_lang=None):
        out = list(segments)
        if out:
            out[0] = (out[0] or "") + " [CHANGED]"
        return out


def test_noop_guard_raises_and_writes_status(tmp_path: Path):
    """
    When allow_noop is False and no paragraphs change, EPUBTranslator must raise TranslationError
    and write a translate_noop status event.
    """
    input_epub = tmp_path / "in.epub"
    output_epub = tmp_path / "out.epub"
    status_file = tmp_path / "status.jsonl"

    _make_minimal_epub(input_epub, ["First paragraph.", "Second paragraph.", "Third paragraph."])

    engine = EPUBTranslator(
        translator=EchoTranslator(),
        debug_mode=False,
        debug_dir=None,
        status_file=status_file,
        allow_noop=False,           # default behavior
        min_changed_ratio=0.0       # default threshold
    )

    with pytest.raises(TranslationError):
        engine.translate_epub(str(input_epub), str(output_epub), to_lang="en", from_lang=None, debug=False)

    # Ensure status file contains translate_noop
    assert status_file.exists()
    events = [json.loads(line) for line in status_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    stages = [e.get("stage") for e in events if e.get("event") == "translate"]
    assert "translate_noop" in stages


def test_allow_noop_succeeds(tmp_path: Path):
    """
    When allow_noop is True, even if nothing changes, EPUBTranslator should produce an output file.
    """
    input_epub = tmp_path / "in.epub"
    output_epub = tmp_path / "out.epub"

    _make_minimal_epub(input_epub, ["Only paragraph here."])

    engine = EPUBTranslator(
        translator=EchoTranslator(),
        debug_mode=False,
        debug_dir=None,
        status_file=None,
        allow_noop=True,            # override to allow no-op output
        min_changed_ratio=0.0
    )

    result = engine.translate_epub(str(input_epub), str(output_epub), to_lang="en", from_lang=None, debug=False)
    assert Path(result).exists()


def test_min_changed_ratio_enforced(tmp_path: Path):
    """
    Enforce min_changed_ratio: if ratio <= threshold, raise; otherwise succeed.
    Use 3 paragraphs, change only 1 => ratio = 1/3 ≈ 0.333.
    """
    input_epub = tmp_path / "in.epub"
    output_epub1 = tmp_path / "out_fail.epub"
    output_epub2 = tmp_path / "out_ok.epub"

    _make_minimal_epub(input_epub, ["P1", "P2", "P3"])

    # Threshold higher than ratio -> should fail
    engine_fail = EPUBTranslator(
        translator=OneChangeTranslator(),
        debug_mode=False,
        debug_dir=None,
        status_file=None,
        allow_noop=False,
        min_changed_ratio=0.5
    )
    with pytest.raises(TranslationError):
        engine_fail.translate_epub(str(input_epub), str(output_epub1), to_lang="en", from_lang=None, debug=False)

    # Threshold lower than ratio -> should succeed
    engine_ok = EPUBTranslator(
        translator=OneChangeTranslator(),
        debug_mode=False,
        debug_dir=None,
        status_file=None,
        allow_noop=False,
        min_changed_ratio=0.3
    )
    result = engine_ok.translate_epub(str(input_epub), str(output_epub2), to_lang="en", from_lang=None, debug=False)
    assert Path(result).exists()
