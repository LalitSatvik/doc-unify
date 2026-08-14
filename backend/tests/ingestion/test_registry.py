from pathlib import Path

import pytest

from app.ingestion.docx import DocxExtractor
from app.ingestion.image import ImageExtractor
from app.ingestion.pdf import PDFExtractor
from app.ingestion.pptx import PptxExtractor
from app.ingestion.registry import UnsupportedFormatError, get_extractor


@pytest.mark.parametrize(
    ("filename", "expected_type"),
    [
        ("report.pdf", PDFExtractor),
        ("report.PDF", PDFExtractor),
        ("scan.png", ImageExtractor),
        ("scan.jpg", ImageExtractor),
        ("scan.jpeg", ImageExtractor),
        ("memo.docx", DocxExtractor),
        ("deck.pptx", PptxExtractor),
    ],
)
def test_get_extractor_picks_by_extension(filename: str, expected_type: type) -> None:
    extractor = get_extractor(Path(filename))
    assert isinstance(extractor, expected_type)


def test_get_extractor_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFormatError, match=r"\.xyz"):
        get_extractor(Path("mystery.xyz"))
