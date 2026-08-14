from app.schema.candidates import CandidateField
from app.schema.clustering import cluster_candidates


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
