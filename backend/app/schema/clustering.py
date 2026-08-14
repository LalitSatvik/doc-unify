"""Groups likely-equivalent candidate fields by embedding proximity
(e.g. "Total Revenue", "Net Sales", "Top-line") -- cheap enough to run
across a whole corpus; the LLM only has to review clusters, not every
pairwise candidate."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.schema.candidates import CandidateField

DEFAULT_DISTANCE_THRESHOLD = 0.15


def cluster_candidates(
    candidates: list[CandidateField],
    embeddings: list[list[float]],
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> list[list[int]]:
    """Returns groups of candidate indices whose label/definition
    embeddings are within `distance_threshold` cosine distance."""
    if not candidates:
        return []
    if len(candidates) == 1:
        return [[0]]

    vectors = np.array(embeddings)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    ).fit(vectors)

    groups: dict[int, list[int]] = {}
    for index, label in enumerate(clustering.labels_):
        groups.setdefault(int(label), []).append(index)
    return list(groups.values())
