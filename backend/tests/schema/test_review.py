from app.llm.base import LLMResponse
from app.schema.candidates import CandidateField
from app.schema.review import review_cluster
from tests.support.scripted_llm import ScriptedLLMProvider


def _candidate(label: str, value: str = "1", definition: str | None = None) -> CandidateField:
    return CandidateField(
        label=label, value=value, unit=None, definition=definition, document_id="d", page=1, snippet=label
    )


async def test_review_cluster_returns_canonical_name_and_definition() -> None:
    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "canonical_name": "Total Revenue",
                    "definition": "Total revenue recognized in the period.",
                    "has_conflict": False,
                }
            )
        ]
    )
    members = [_candidate("Total Revenue"), _candidate("Net Sales")]

    review = await review_cluster(provider, members)

    assert review.canonical_name == "Total Revenue"
    assert review.has_conflict is False
    assert review.conflict_reason is None
    assert review.member_labels == ["Total Revenue", "Net Sales"]


async def test_review_cluster_flags_conflicting_methodology() -> None:
    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "canonical_name": "Revenue (mixed methodology)",
                    "definition": "Ambiguous -- members use different accounting bases.",
                    "has_conflict": True,
                    "conflict_reason": "One member is GAAP revenue, the other is non-GAAP.",
                }
            )
        ]
    )
    members = [
        _candidate("GAAP Revenue", definition="Revenue per GAAP"),
        _candidate("Adjusted Revenue", definition="Non-GAAP adjusted revenue"),
    ]

    review = await review_cluster(provider, members)

    assert review.has_conflict is True
    assert "GAAP" in review.conflict_reason
