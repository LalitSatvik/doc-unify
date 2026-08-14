"""Documented stub for future video ingestion (frame sampling + transcript
extraction). Not implemented in this phase — see docs/plan.md ("Video
ingestion is explicitly deferred"). Registered against the `Extractor`
interface now so the eventual implementation is a drop-in, not a rework.
"""

from __future__ import annotations

from pathlib import Path

from app.ingestion.base import ContentBlock, Extractor


class VideoExtractor(Extractor):
    def extract(self, file_path: Path, document_id: str) -> list[ContentBlock]:
        raise NotImplementedError("Video ingestion is not implemented yet.")
