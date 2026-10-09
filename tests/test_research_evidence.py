from nn_genai.infrastructure.agents.research_tools import rank_search_results
from nn_genai.application.research.source_quality import (
    SourceQuality,
    classify_source_quality,
)
import pytest
from pydantic import ValidationError

from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.application.research.provenance_validator import (
    InsufficientEvidenceError,
    InvalidEvidenceReferenceError,
    ProvenanceValidator,
)
from nn_genai.application.research.url_normalizer import normalize_url
from nn_genai.models.research_status import ResearchStatus
from nn_genai.models.search_result import SearchResult
from nn_genai.models.research_draft import EvidenceCitationDraft, ResearchDraft
from nn_genai.models.retrieved_evidence import RetrievedEvidence


def make_evidence(
    evidence_id: str = "evidence-1234567890ab",
) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id,
        title="Einstein and Relativity",
        url="https://example.com/einstein",
        snippet="Einstein developed the theory of general relativity.",
    )


def make_draft(evidence_id: str = "evidence-1234567890ab") -> ResearchDraft:
    return ResearchDraft(
        person_name="Albert Einstein",
        selected_work="Theory of relativity",
        status=ResearchStatus.CONCLUSIVE,
        reasoning="Relativity transformed modern physics.",
        citations=[
            EvidenceCitationDraft(
                evidence_id=evidence_id,
                supporting_claim=(
                    "Einstein developed the theory of general relativity."
                ),
            )
        ],
        confidence=0.95,
    )


def test_ledger_adds_and_retrieves_evidence() -> None:
    ledger = EvidenceLedger()
    evidence = make_evidence()

    ledger.add(evidence)

    assert ledger.get(evidence.evidence_id) == evidence
    assert ledger.all() == [evidence]


def test_rejects_fabricated_evidence_id() -> None:
    ledger = EvidenceLedger()
    ledger.add(make_evidence())

    with pytest.raises(
        InvalidEvidenceReferenceError,
        match="not returned by search",
    ):
        ProvenanceValidator().build_result(
            draft=make_draft("evidence-1114567890ab"),
            ledger=ledger,
        )


def test_build_result_preserves_result_status() -> None:
    ledger = EvidenceLedger()
    evidence = make_evidence()
    ledger.add(evidence)

    result = ProvenanceValidator().build_result(
        draft=make_draft(evidence.evidence_id),
        ledger=ledger,
    )

    assert result.status is ResearchStatus.CONCLUSIVE


def test_rejects_research_when_ledger_is_empty() -> None:
    with pytest.raises(
        InsufficientEvidenceError,
        match="no retrievable evidence",
    ):
        ProvenanceValidator().build_result(
            draft=make_draft(),
            ledger=EvidenceLedger(),
        )


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("https://EXAMPLE.com/article/", "https://example.com/article"),
        (
            "https://example.com/article?utm_source=test&id=42#section",
            "https://example.com/article?id=42",
        ),
        (
            "https://example.com:443/article?b=2&a=1",
            "https://example.com/article?a=1&b=2",
        ),
    ],
)
def test_normalize_url(raw_url: str, expected: str) -> None:
    assert normalize_url(raw_url) == expected


def test_normalize_url_rejects_unsupported_scheme() -> None:
    with pytest.raises(ValueError, match="Unsupported evidence URL"):
        normalize_url("ftp://example.com/article")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://www.nobelprize.org/prizes/physics/",
            SourceQuality.PRIMARY,
        ),
        (
            "https://physics.mit.edu/research/",
            SourceQuality.AUTHORITATIVE,
        ),
        (
            "https://www.britannica.com/biography/Albert-Einstein",
            SourceQuality.SECONDARY,
        ),
        (
            "https://en.wikipedia.org/wiki/Albert_Einstein",
            SourceQuality.SECONDARY,
        ),
        (
            "https://example.com/einstein",
            SourceQuality.OTHER,
        ),
    ],
)
def test_classifies_source_quality(
    url: str,
    expected: SourceQuality,
) -> None:
    assert classify_source_quality(url) is expected


def test_does_not_accept_domain_suffix_impersonation() -> None:
    assert (
        classify_source_quality(
            "https://fakewikipedia.org/einstein"
        )
        is SourceQuality.OTHER
    )


def test_ranks_quality_without_losing_results() -> None:

    results = [
        SearchResult(
            title="Other", url="https://example.com/article", snippet=""),
        SearchResult(title="Primary",
                     url="https://nobelprize.org/einstein", snippet=""),
        SearchResult(title="University",
                     url="https://physics.mit.edu/einstein", snippet=""),
        SearchResult(title="Secondary",
                     url="https://britannica.com/einstein", snippet=""),
    ]

    ranked = rank_search_results(results)

    assert [result.title for result in ranked] == [
        "Primary",
        "University",
        "Secondary",
        "Other",
    ]


def test_preserves_provider_order_within_same_category() -> None:
    results = [
        SearchResult(
            title="First", url="https://example-one.com/article", snippet=""),
        SearchResult(title="Second",
                     url="https://example-two.com/article", snippet=""),
    ]

    ranked = rank_search_results(results)

    assert [result.title for result in ranked] == [
        "First",
        "Second",
    ]


def test_rejects_conclusive_draft_without_citations() -> None:
    with pytest.raises(
        ValueError,
        match="conclusive result requires retrieved evidence",
    ):
        ResearchDraft(
            person_name="Albert Einstein",
            status=ResearchStatus.CONCLUSIVE,
            selected_work="General relativity",
            reasoning="General relativity was highly influential.",
            citations=[],
            confidence=0.9,
        )


def test_allows_inconclusive_draft_without_citations() -> None:
    draft = ResearchDraft(
        person_name="Unknown Person",
        status=ResearchStatus.INCONCLUSIVE,
        selected_work=None,
        reasoning="Available evidence was insufficient.",
        citations=[],
        confidence=0.2,
    )

    assert draft.citations == []


def test_inconclusive_result_still_rejects_fabricated_evidence() -> None:
    ledger = EvidenceLedger()
    ledger.add(make_evidence())

    draft = ResearchDraft(
        person_name="Unknown Person",
        status=ResearchStatus.INCONCLUSIVE.value,
        selected_work=None,
        reasoning="The available evidence was insufficient.",
        citations=[
            EvidenceCitationDraft(
                evidence_id="evidence-0123456789ab",
                supporting_claim="An unsupported claim.",
            )
        ],
        confidence=0.2,
    )

    with pytest.raises(InvalidEvidenceReferenceError):
        ProvenanceValidator().build_result(
            draft=draft,
            ledger=ledger,
        )
