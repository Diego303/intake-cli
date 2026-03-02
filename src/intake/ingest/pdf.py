"""Parser for PDF files using pdfplumber.

Supports: .pdf files with extractable text and tables.
Extracts: Full text, tables as Markdown, page-level sections, metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from intake.ingest.base import ParsedContent, ParseError, validate_file_readable

logger = structlog.get_logger()


class PdfParser:
    """Parser for PDF documents.

    Supports:
    - PDF files with extractable text
    - Tables within PDFs (converted to Markdown)
    - Multi-page documents with page-level sections

    Extracts:
    - Full text from all pages
    - Tables as Markdown-formatted text
    - Page count and metadata
    """

    def can_parse(self, source: str) -> bool:
        """Check if this source is a parseable PDF file."""
        path = Path(source)
        return path.exists() and path.is_file() and path.suffix.lower() == ".pdf"

    def parse(self, source: str) -> ParsedContent:
        """Parse a PDF file into normalized content.

        Args:
            source: Path to the PDF file.

        Returns:
            ParsedContent with extracted text and table data.

        Raises:
            ParseError: If the PDF cannot be read or contains no extractable text.
        """
        path = validate_file_readable(source)

        try:
            import pdfplumber
        except ImportError as e:
            raise ParseError(
                source=source,
                reason="pdfplumber is not installed",
                suggestion="Install it with: pip install pdfplumber",
            ) from e

        try:
            pdf = pdfplumber.open(path)
        except Exception as e:
            raise ParseError(
                source=source,
                reason=f"Could not open PDF: {e}",
                suggestion="Verify the file is a valid PDF.",
            ) from e

        text_parts: list[str] = []
        sections: list[dict[str, str]] = []

        with pdf:
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                table_text = self._extract_tables(page)

                page_content = page_text
                if table_text:
                    page_content += "\n\n" + table_text

                if page_content.strip():
                    text_parts.append(page_content)
                    sections.append({
                        "title": f"Page {i}",
                        "content": page_content.strip(),
                    })

            page_count = len(pdf.pages)

        if not text_parts:
            raise ParseError(
                source=source,
                reason="PDF contains no extractable text",
                suggestion=(
                    "This PDF may contain only scanned images. "
                    "Try using it as an image source instead."
                ),
            )

        full_text = "\n\n---\n\n".join(text_parts)
        metadata: dict[str, str] = {
            "page_count": str(page_count),
            "source_type": "pdf",
        }

        logger.info(
            "pdf_parsed",
            source=source,
            pages=page_count,
            sections=len(sections),
        )

        return ParsedContent(
            text=full_text,
            format="pdf",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    def _extract_tables(self, page: Any) -> str:
        """Extract tables from a PDF page and format as Markdown."""
        try:
            tables = page.extract_tables()
        except Exception:
            return ""

        if not tables:
            return ""

        parts: list[str] = []
        for table in tables:
            if not table or not table[0]:
                continue
            md = self._table_to_markdown(table)
            if md:
                parts.append(md)
        return "\n\n".join(parts)

    def _table_to_markdown(self, table: list[list[str | None]]) -> str:
        """Convert a table (list of rows) to Markdown format."""
        if not table:
            return ""

        rows: list[list[str]] = []
        for raw_row in table:
            cleaned = [(cell or "").strip().replace("\n", " ") for cell in raw_row]
            rows.append(cleaned)

        if not rows:
            return ""

        header = rows[0]
        lines: list[str] = []
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")

        for row in rows[1:]:
            padded = list(row)
            while len(padded) < len(header):
                padded.append("")
            lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        return "\n".join(lines)
