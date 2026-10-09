import asyncio

from nn_genai.config import Settings, settings

from nn_genai.infrastructure.agents.research_tools import (
    create_search_tool,
)
from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.infrastructure.search.tavily_search_provider import (
    TavilySearchProvider,
)


async def main() -> None:
    provider = TavilySearchProvider(
        api_key=Settings.require_secret(
            settings.tavily_api_key, "TAVILY_API_KEY"
        ),
        max_results=5,
    )

    search_web = create_search_tool(provider, EvidenceLedger())

    result = await search_web.ainvoke(
        {
            "query": (
                "Albert Einstein most significant "
                "scientific contribution"
            )
        }
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
