"""Image extractor: OCR via pytesseract. Produces a single IMAGE block
holding the recognized text (images have no intrinsic page/table structure)."""

from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image

from app.ingestion.base import BlockType, ContentBlock, Extractor


class ImageExtractor(Extractor):
    def extract(self, file_path: Path, document_id: str) -> list[ContentBlock]:
        with Image.open(file_path) as image:
            text = pytesseract.image_to_string(image)

        if not text.strip():
            return []

        return [
            ContentBlock(
                document_id=document_id,
                page=1,
                block_type=BlockType.IMAGE,
                text=text,
            )
        ]
