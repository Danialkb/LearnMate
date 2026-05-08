from __future__ import annotations

import re
from html.parser import HTMLParser
from io import BytesIO

from pypdf import PdfReader

from services.documents.chunking import TextBlock
from services.documents.enums import DocumentFormat


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if cleaned:
            self._parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self._parts)


class DocumentTextExtractor:
    def extract(
        self, *, data: bytes, document_format: DocumentFormat
    ) -> list[TextBlock]:
        match document_format:
            case DocumentFormat.TXT | DocumentFormat.MARKDOWN:
                return [TextBlock(text=self._decode_text(data))]
            case DocumentFormat.WEB_PAGE:
                return [TextBlock(text=self._extract_html(data))]
            case DocumentFormat.PDF:
                return self._extract_pdf(data)
            case DocumentFormat.DOCX:
                raise NotImplementedError("DOCX text extraction is not implemented yet")

    @staticmethod
    def _decode_text(data: bytes) -> str:
        return data.decode("utf-8", errors="replace")

    def _extract_html(self, data: bytes) -> str:
        parser = _HTMLTextParser()
        parser.feed(self._decode_text(data))
        return re.sub(r"\n{3,}", "\n\n", parser.text()).strip()

    @staticmethod
    def _extract_pdf(data: bytes) -> list[TextBlock]:
        reader = PdfReader(BytesIO(data))
        blocks: list[TextBlock] = []
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
            if not cleaned:
                continue
            blocks.append(
                TextBlock(
                    text=cleaned,
                    page_start=page_index,
                    page_end=page_index,
                )
            )
        return blocks
