import pytest

from nn_genai.application.research.provenance_validator import (
    ProvenanceValidator,
)
from nn_genai.infrastructure.agents.langchain_research_agent import (
    LangChainResearchAgent,
)
from nn_genai.models.search_result import SearchResult

from tests.fakes.fake_research_model import FakeResearchModel
from tests.fakes.fake_search_provider import FakeSearchProvider


@pytest.mark.asyncio
async def test_research_calls_search_before_result_validation() -> None:
    provider = FakeSearchProvider(
        results=[
            SearchResult(
                title="Einstein and Relativity",
                url="https://example.com/einstein",
                snippet=(
                    "Einstein developed the theories of special "
                    "and general relativity."
                ),
            )
        ]
    )

    agent = LangChainResearchAgent(
        model=FakeResearchModel(),
        search_provider=provider,
        provenance_validator=ProvenanceValidator(),
    )

    result = await agent.research("Albert Einstein")

    assert result.selected_work == "Theory of relativity"
    assert result.status.value == "conclusive"
    assert len(result.sources) == 1
    assert provider.queries == [
        "Albert Einstein most significant scientific contribution"
    ]


@pytest.mark.asyncio
async def test_research_rejects_empty_person_name() -> None:
    provider = FakeSearchProvider([])

    agent = LangChainResearchAgent(
        model=FakeResearchModel(),
        search_provider=provider,
        provenance_validator=ProvenanceValidator(),
    )

    with pytest.raises(
        ValueError,
        match="person_name cannot be empty",
    ):
        await agent.research("   ")
        