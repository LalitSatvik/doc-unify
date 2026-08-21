from pathlib import Path

from PIL import Image, ImageDraw

from app.ingestion.base import BlockType
from app.ingestion.image import ImageExtractor


def test_ocr_extracts_text_from_image(tmp_path: Path) -> None:
    img = Image.new("RGB", (700, 200), "white")
    draw = ImageDraw.Draw(img)
    # No system font path here (was hardcoded to macOS's Arial.ttf, which
    # doesn't exist on Linux CI runners) -- PIL's built-in default bitmap
    # font is enough for tesseract to read back, same as the scanned-PDF
    # fixture in pdf_fixtures.py.
    draw.text((20, 80), "Total Assets 555000", fill="black")
    img_path = tmp_path / "scan.png"
    img.save(img_path)

    blocks = ImageExtractor().extract(img_path, document_id="doc-1")

    assert len(blocks) == 1
    assert blocks[0].block_type == BlockType.IMAGE
    assert blocks[0].page == 1
    assert blocks[0].document_id == "doc-1"
    assert "Total Assets" in blocks[0].text
    assert "555000" in blocks[0].text
