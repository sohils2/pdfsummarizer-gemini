from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from pdf_processor import PDFProcessor


def make_pdf(text: str) -> BytesIO:
    """Build a tiny one-page PDF whose content stream contains ``text``."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 72 700 Td ({text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(content)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    page[NameObject("/Resources")] = writer._add_object(resources)
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer


def test_extract_text_and_metadata() -> None:
    processor = PDFProcessor()
    pdf = make_pdf("Hello PDF summarizer. Second sentence.")

    assert "Hello PDF summarizer" in processor.extract_text_from_pdf(pdf)
    metadata = processor.get_pdf_metadata(pdf)
    assert metadata["num_pages"] == 1
    assert metadata["title"] == "Unknown"


def test_clean_text_keeps_punctuation_and_paragraphs() -> None:
    processor = PDFProcessor()
    raw = "  Hello\x00 world.  \n\n\n\nNext\tline costs $5 (really)!  "

    assert processor.clean_text(raw) == "Hello world.\n\nNext line costs $5 (really)!"


def test_count_tokens_and_chunking_respect_limit() -> None:
    processor = PDFProcessor()
    text = "First sentence is here. Second sentence follows. Third one ends it."
    assert processor.count_tokens(text) > 0

    chunks = processor.chunk_text(text, max_tokens=5)
    assert len(chunks) > 1
    assert all(processor.count_tokens(chunk) <= 6 for chunk in chunks)
    assert " ".join(chunks)


def test_chunk_text_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="scanned images"):
        PDFProcessor().chunk_text("   ")


def test_chunk_text_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        PDFProcessor().chunk_text("Some text.", max_tokens=0)
