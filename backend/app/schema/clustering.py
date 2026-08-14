"""Groups likely-equivalent candidate fields by embedding proximity
(e.g. "Total Revenue", "Net Sales", "Top-line") -- cheap enough to run
across a whole corpus; the LLM only has to review clusters, not every
pairwise candidate."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.schema.candidates import CandidateField

# Calibrated against measured nomic-embed-text label-embedding cosine
# distances on real financial-report labels: true synonyms ("Total
# Revenue" / "Net Sales") measured ~0.35 apart; a distinct but
# topically-related metric ("Net Income") measured ~0.46 from "Total
# Revenue". 0.36 sits between the two. Re-measure if the embed model
# changes -- the right value is model-specific, not universal.
DEFAULT_DISTANCE_THRESHOLD = 0.36


def cluster_candidates(
    candidates: list[CandidateField],
    embeddings: list[list[float]],
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> list[list[int]]:
    """Returns groups of candidate indices whose label embeddings are
    within `distance_threshold` cosine distance."""
    if not candidates:
        return []
    if len(candidates) == 1:
        return [[0]]

    vectors = np.array(embeddings)
    # Complete linkage: a candidate only joins a cluster if it's within
    # `distance_threshold` of *every* member, not just close on average.
    # With small per-corpus candidate counts, average linkage let one
    # noisy pair chain-drag unrelated fields into the same cluster
    # (e.g. "Headcount" merging into "Revenue"); complete linkage trades
    # some recall for that precision, matching the product's stance that
    # a missed merge is recoverable (user merges manually) while a false
    # merge silently hides a real distinction.
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="complete",
    ).fit(vectors)

    groups: dict[int, list[int]] = {}
    for index, label in enumerate(clustering.labels_):
        groups.setdefault(int(label), []).append(index)
    return list(groups.values())
