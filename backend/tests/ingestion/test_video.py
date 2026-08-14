from pathlib import Path

import pytest

from app.ingestion.video import VideoExtractor


def test_video_extraction_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        VideoExtractor().extract(Path("clip.mp4"), document_id="doc-1")
