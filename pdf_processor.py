"""PDF text extraction, cleaning, token counting and chunking."""

from __future__ import annotations

import logging
import re

import tiktoken
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Turn an uploaded PDF into token-limited text chunks."""

    def __init__(self) -> None:
        # cl100k_base is an approximation of Gemini's tokenizer; the UI labels
        # the count as approximate rather than exact.
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Return all page text; pages that fail to extract are skipped."""
        try:
            pdf_file.seek(0)
            reader = PdfReader(pdf_file)
            pages: list[str] = []
            for page_number, page in enumerate(reader.pages, 1):
                try:
                    pages.append(page.extract_text() or "")
                except Exception as exc:  # noqa: BLE001 - one bad page should not abort the file
                    logger.warning("Skipping page %d: %s", page_number, exc)
            return "\n\n".join(pages)
        except Exception as exc:
            raise RuntimeError(f"Error reading PDF: {exc}") from exc

    def clean_text(self, text: str) -> str:
        """Remove control characters and normalise whitespace, keeping punctuation."""
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def count_tokens(self, text: str) -> int:
        """Approximate token count used for chunk sizing and statistics."""
        return len(self.encoding.encode(text, disallowed_special=()))

    def chunk_text(self, text: str, max_tokens: int = 8000) -> list[str]:
        """Split text into chunks of at most ``max_tokens`` tokens.

        Splitting prefers sentence boundaries. A single sentence longer than
        the limit is hard-split by tokens.
        """
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if not text.strip():
            raise ValueError("No extractable text — the PDF may be scanned images")

        pieces: list[tuple[str, int]] = []
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            tokens = self.encoding.encode(sentence, disallowed_special=())
            if len(tokens) > max_tokens:
                pieces.extend(
                    (
                        self.encoding.decode(tokens[i : i + max_tokens]),
                        min(max_tokens, len(tokens) - i),
                    )
                    for i in range(0, len(tokens), max_tokens)
                )
            else:
                pieces.append((sentence, len(tokens)))

        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for piece, size in pieces:
            if current and current_tokens + size + 1 > max_tokens:
                chunks.append(" ".join(current))
                current, current_tokens = [], 0
            current.append(piece)
            current_tokens += size + 1  # +1 approximates the joining space
        if current:
            chunks.append(" ".join(current))
        return chunks

    def get_pdf_metadata(self, pdf_file) -> dict:
        """Return page count, title, author and subject, or an ``error`` key."""
        try:
            pdf_file.seek(0)
            reader = PdfReader(pdf_file)
            metadata = reader.metadata or {}

            def field(key: str) -> str:
                return metadata.get(key) or "Unknown"

            return {
                "num_pages": len(reader.pages),
                "title": field("/Title"),
                "author": field("/Author"),
                "subject": field("/Subject"),
            }
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI as a warning
            return {"error": str(exc)}
