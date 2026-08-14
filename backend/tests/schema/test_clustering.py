import math

from app.schema.candidates import CandidateField
from app.schema.clustering import DEFAULT_DISTANCE_THRESHOLD, cluster_candidates


def _candidate(label: str) -> CandidateField:
    return CandidateField(
        label=label, value="1", unit=None, definition=None, document_id="d", page=1, snippet=label
    )


def test_groups_near_identical_embeddings_together() -> None:
    candidates = [_candidate("Total Revenue"), _candidate("Net Sales"), _candidate("Headcount")]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.98, 0.02, 0.0],  # nearly identical to Total Revenue
        [0.0, 0.0, 1.0],  # unrelated
    ]

    groups = cluster_candidates(candidates, embeddings, distance_threshold=0.1)

    group_labels = [sorted(candidates[i].label for i in group) for group in groups]
    assert sorted(group_labels) == [["Headcount"], ["Net Sales", "Total Revenue"]]


def test_single_candidate_is_its_own_group() -> None:
    candidates = [_candidate("Total Revenue")]
    groups = cluster_candidates(candidates, [[1.0, 0.0]])
    assert groups == [[0]]


def test_empty_candidates_returns_no_groups() -> None:
    assert cluster_candidates([], []) == []


def _at_cosine_distance_on_axis(distance: float, axis: int, dim: int = 3) -> list[float]:
    """A unit vector at exactly `distance` cosine distance from
    [1, 0, ..., 0], displaced along `axis` -- placing two such vectors on
    *different* axes keeps their distance from each other independent of
    their (individually controlled) distance from the shared base point,
    unlike two points in a single 2D plane relative to that base."""
    angle = math.acos(1 - distance)
    v = [0.0] * dim
    v[0] = math.cos(angle)
    v[axis] = math.sin(angle)
    return v


def test_default_threshold_merges_true_synonyms_but_not_related_distinct_metrics() -> None:
    """Calibrated against measured nomic-embed-text label-embedding cosine
    distances for real financial-report label pairs: true synonyms like
    "Total Revenue" / "Net Sales" measured ~0.35 apart, while a genuinely
    distinct (but topically related) metric like "Net Income" measured
    ~0.46 apart from "Total Revenue". The default threshold must sit
    between those two, or discovery either misses real synonyms or
    conflates distinct metrics."""
    candidates = [_candidate("Total Revenue"), _candidate("Net Sales"), _candidate("Net Income")]
    embeddings = [
        [1.0, 0.0, 0.0],
        _at_cosine_distance_on_axis(0.35, axis=1),
        _at_cosine_distance_on_axis(0.46, axis=2),
    ]

    groups = cluster_candidates(candidates, embeddings, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)

    group_labels = [sorted(candidates[i].label for i in group) for group in groups]
    assert sorted(group_labels) == [["Net Income"], ["Net Sales", "Total Revenue"]]
