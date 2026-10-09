import pytest

from nn_genai.infrastructure.agents.research_tools import create_search_tool
from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.models.search_result import SearchResult
from tests.fakes.fake_search_provider import FakeSearchProvider


@pytest.mark.asyncio
async def test_search_web_calls_provider_and_records_evidence() -> None:
    provider = FakeSearchProvider(
        results=[
            SearchResult(
                title="Albert Einstein",
                url="https://example.com/einstein",
                snippet="Einstein developed the theory of relativity.",
            )
        ]
    )
    ledger = EvidenceLedger()
    search_web = create_search_tool(provider, ledger)

    result = await search_web.ainvoke(
        {"query": "Albert Einstein theory of relativity"}
    )

    assert provider.queries == ["Albert Einstein theory of relativity"]
    assert "Albert Einstein" in result
    assert "Evidence ID: evidence-" in result
    assert "URL: https://example.com/einstein" in result
    assert "Snippet: Einstein developed the theory of relativity." in result

    evidence = ledger.all()
    assert len(evidence) == 1
    assert evidence[0].title == "Albert Einstein"
    assert str(evidence[0].url).rstrip("/") == "https://example.com/einstein"


@pytest.mark.asyncio
async def test_search_web_returns_no_results_without_recording_evidence() -> None:
    provider = FakeSearchProvider([])
    ledger = EvidenceLedger()
    search_web = create_search_tool(provider, ledger)

    result = await search_web.ainvoke({"query": "Albert Einstein"})

    assert result == "No search results found."
    assert provider.queries == ["Albert Einstein"]
    assert ledger.all() == []


@pytest.mark.asyncio
async def test_search_web_uses_stable_id_for_normalized_url() -> None:
    provider = FakeSearchProvider(
        results=[
            SearchResult(
                title="First result",
                url="https://EXAMPLE.com/einstein/?utm_source=test",
                snippet="First snippet.",
            ),
            SearchResult(
                title="Duplicate result",
                url="https://example.com/einstein",
                snippet="Duplicate snippet.",
            ),
        ]
    )
    ledger = EvidenceLedger()
    search_web = create_search_tool(provider, ledger)

    result = await search_web.ainvoke({"query": "Einstein"})

    evidence_ids = [
        line.removeprefix("Evidence ID: ")
        for line in result.splitlines()
        if line.startswith("Evidence ID: ")
    ]
    assert len(evidence_ids) == 2
    assert evidence_ids[0] == evidence_ids[1]
    assert len(ledger.all()) == 1


@pytest.mark.asyncio
async def test_search_web_returns_no_results_message() -> None:
    provider = FakeSearchProvider([])
    ledger = EvidenceLedger()

    search_tool = create_search_tool(
        provider,
        ledger,
    )

    result = await search_tool.ainvoke(
        {"query": "Albert Einstein"}
    )

    assert result == "No search results found."
    assert provider.queries == ["Albert Einstein"]
    assert ledger.all() == []
