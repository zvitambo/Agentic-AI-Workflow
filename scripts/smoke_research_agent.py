import asyncio
import os
from collections.abc import Sequence
from nn_genai.application.research.provenance_validator import ProvenanceValidator
from nn_genai.config import Settings, settings
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from nn_genai.infrastructure.agents.langchain_research_agent import (
    LangChainResearchAgent,
)
from nn_genai.infrastructure.search.tavily_search_provider import (
    TavilySearchProvider,
)
from nn_genai.models.search_result import SearchResult



class TrackingSearchProvider:
    """Records real Tavily queries and results for smoke-test assertions."""

    def __init__(self, delegate: TavilySearchProvider) -> None:
        self._delegate = delegate
        self.queries: list[str] = []
        self.results: list[SearchResult] = []

    async def search(self, query: str) -> Sequence[SearchResult]:
        self.queries.append(query)

        results = await self._delegate.search(query)
        self.results.extend(results)

        return results


def require_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"{name} is required to run the research-agent smoke test."
        )

    return value


async def main() -> None:
    google_api_key = require_environment_variable("GOOGLE_API_KEY")
    model = ChatGoogleGenerativeAI(
        model=os.getenv(
            "GEMINI_RESEARCH_MODEL",
            "gemini-3.6-flash",
        ),
        api_key=SecretStr(google_api_key),
        temperature=0,
        max_retries=2,
    )

    tavily = TavilySearchProvider(
        api_key=Settings.require_secret(
            settings.tavily_api_key, "TAVILY_API_KEY"
        ),
        max_results=15,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.max_retry_attempts,
        retry_base_delay_seconds=settings.retry_base_delay_seconds,
    )
    tracking_provider = TrackingSearchProvider(tavily)
    provenance_provider = ProvenanceValidator()

    agent = LangChainResearchAgent(
        model=model,
        search_provider=tracking_provider,
        provenance_validator=provenance_provider,
        max_searches=settings.max_searches,
        recursion_limit=settings.agent_recursion_limit,
        timeout_seconds=settings.research_timeout_seconds,
    )

    result = await agent.research("Albert Einstein")

    if not tracking_provider.queries:
        raise AssertionError(
            "Smoke test failed: the agent returned a result without "
            "calling search_web."
        )

    returned_urls = {
        source.url
        for source in result.sources
    }
    searched_urls = {
        search_result.url
        for search_result in tracking_provider.results
    }

    ungrounded_urls = returned_urls - searched_urls

    if ungrounded_urls:
        raise AssertionError(
            "Smoke test failed: ResearchResult contains URLs that were "
            f"not returned by Tavily: {sorted(ungrounded_urls)}"
        )

    print("\nSmoke test passed.")
    print("\nSearch queries:")
    for query in tracking_provider.queries:
        print(f"- {query}")

    print("\nStructured result:")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
