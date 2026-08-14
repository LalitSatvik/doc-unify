"""Synthetic PDF builders for ingestion tests — no binary fixtures checked
into the repo; every test PDF is generated on the fly with pymupdf."""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw


def make_text_pdf(path: Path, pages: list[str]) -> None:
    doc = pymupdf.open()
    for page_text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), page_text, fontsize=12)
    doc.save(path)
    doc.close()


def make_table_pdf(path: Path, rows: list[list[str]]) -> None:
    doc = pymupdf.open()
    page = doc.new_page()

    x0, y0, cell_w, cell_h = 72, 72, 100, 30
    n_rows, n_cols = len(rows), len(rows[0])

    for r in range(n_rows + 1):
        page.draw_line((x0, y0 + r * cell_h), (x0 + n_cols * cell_w, y0 + r * cell_h))
    for c in range(n_cols + 1):
        page.draw_line((x0 + c * cell_w, y0), (x0 + c * cell_w, y0 + n_rows * cell_h))

    for r in range(n_rows):
        for c in range(n_cols):
            page.insert_text((x0 + c * cell_w + 5, y0 + r * cell_h + 20), rows[r][c], fontsize=10)

    doc.save(path)
    doc.close()


def make_scanned_pdf(path: Path, text: str) -> None:
    """A page with no extractable text layer — just a burned-in image, like
    a scanned document — to exercise the OCR fallback."""
    img = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    doc = pymupdf.open()
    page = doc.new_page(width=600, height=200)
    page.insert_image(pymupdf.Rect(0, 0, 600, 200), stream=buf.getvalue())
    doc.save(path)
    doc.close()
