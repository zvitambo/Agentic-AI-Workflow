import pytest

from nn_genai.application.research.errors import SearchBudgetExceededError
from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.application.research.provenance_validator import ProvenanceValidator
from nn_genai.infrastructure.agents.research_tools import create_search_tool
from nn_genai.models.research_draft import ResearchDraft
from nn_genai.models.research_status import ResearchStatus

from tests.fakes.fake_search_provider import FakeSearchProvider


def test_inconclusive_result_can_contain_no_evidence() -> None:
    draft = ResearchDraft(
        person_name="Unknown Person",
        status=ResearchStatus.INCONCLUSIVE,
        selected_work=None,
        reasoning="No retrieved evidence supported a comparative conclusion.",
        citations=[],
        confidence=0.0,
    )

    result = ProvenanceValidator().build_result(draft, EvidenceLedger())

    assert result.status is ResearchStatus.INCONCLUSIVE
    assert result.selected_work is None
    assert result.sources == []


@pytest.mark.asyncio
async def test_search_tool_enforces_request_budget() -> None:
    provider = FakeSearchProvider([])
    search_tool = create_search_tool(
        provider,
        EvidenceLedger(),
        max_searches=1,
    )

    await search_tool.ainvoke({"query": "first query"})

    with pytest.raises(SearchBudgetExceededError):
        await search_tool.ainvoke({"query": "second query"})


def test_inconclusive_result_rejects_selected_work() -> None:
    with pytest.raises(ValueError, match="must not select a work"):
        ResearchDraft(
            person_name="Unknown Person",
            status=ResearchStatus.INCONCLUSIVE,
            selected_work="Unsupported contribution",
            reasoning="The evidence was insufficient.",
            citations=[],
            confidence=0.2,
        )
