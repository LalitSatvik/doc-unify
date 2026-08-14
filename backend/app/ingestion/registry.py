"""Maps a file extension to its `Extractor`. The one place that needs to
know every supported format."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.base import Extractor
from app.ingestion.docx import DocxExtractor
from app.ingestion.image import ImageExtractor
from app.ingestion.pdf import PDFExtractor
from app.ingestion.pptx import PptxExtractor

_EXTRACTORS_BY_EXTENSION: dict[str, type[Extractor]] = {
    ".pdf": PDFExtractor,
    ".png": ImageExtractor,
    ".jpg": ImageExtractor,
    ".jpeg": ImageExtractor,
    ".docx": DocxExtractor,
    ".pptx": PptxExtractor,
}


class UnsupportedFormatError(ValueError):
    pass


def get_extractor(file_path: Path) -> Extractor:
    extension = file_path.suffix.lower()
    extractor_cls = _EXTRACTORS_BY_EXTENSION.get(extension)
    if extractor_cls is None:
        raise UnsupportedFormatError(f"Unsupported file extension: {extension}")
    return extractor_cls()
