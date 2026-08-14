"""Common `ContentBlock` interface every per-format extractor normalizes
into. Nothing downstream (embedding, schema discovery, extraction) reads a
PDF/image/docx/pptx directly — it reads this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BlockType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


@dataclass
class ContentBlock:
    """One unit of extracted content, tied back to its exact source
    location for provenance (per-cell citations downstream).

    - `text`: required for TEXT/IMAGE blocks (IMAGE blocks hold OCR'd text).
    - `table`: required for TABLE blocks; rows of cell strings, header row
      first when detectable.
    - `bbox`: optional `(x0, top, x1, bottom)` in page coordinates, when the
      extractor can determine it.
    """

    document_id: str
    page: int
    block_type: BlockType
    text: str | None = None
    table: list[list[str]] | None = None
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError(f"page must be >= 1, got {self.page}")

        if self.block_type in (BlockType.TEXT, BlockType.IMAGE) and (
            self.text is None or not self.text.strip()
        ):
            raise ValueError(f"{self.block_type.value} block requires non-empty text")

        if self.block_type is BlockType.TABLE and not self.table:
            raise ValueError("table block requires a non-empty table")


class Extractor(ABC):
    """Extracts `ContentBlock`s from one document file."""

    @abstractmethod
    def extract(self, file_path: Path, document_id: str) -> list[ContentBlock]:
        """Parse `file_path` and return its content blocks in document
        order. `document_id` is stamped onto every block for provenance."""
        raise NotImplementedError
