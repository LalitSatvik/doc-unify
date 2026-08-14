"""PDF extractor: text + table extraction via pdfplumber, with an OCR
fallback (pytesseract, page rendered internally by pdfplumber) for scanned
pages that carry no extractable text layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber
import pytesseract

from app.ingestion.base import BlockType, ContentBlock, Extractor

OCR_RESOLUTION = 200


class PDFExtractor(Extractor):
    def extract(self, file_path: Path, document_id: str) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []

        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                blocks.extend(self._text_blocks(page, page_number, document_id))
                blocks.extend(self._table_blocks(page, page_number, document_id))

        return blocks

    def _text_blocks(self, page: Any, page_number: int, document_id: str) -> list[ContentBlock]:
        text = page.extract_text() or ""
        if not text.strip():
            text = self._ocr_page(page)

        if not text.strip():
            return []

        return [
            ContentBlock(
                document_id=document_id,
                page=page_number,
                block_type=BlockType.TEXT,
                text=text,
                bbox=tuple(page.bbox),
            )
        ]

    def _table_blocks(self, page: Any, page_number: int, document_id: str) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for table in page.find_tables():
            rows = [[cell or "" for cell in row] for row in table.extract()]
            if rows:
                blocks.append(
                    ContentBlock(
                        document_id=document_id,
                        page=page_number,
                        block_type=BlockType.TABLE,
                        table=rows,
                        bbox=tuple(table.bbox),
                    )
                )
        return blocks

    def _ocr_page(self, page: Any) -> str:
        image = page.to_image(resolution=OCR_RESOLUTION).original
        return pytesseract.image_to_string(image)
