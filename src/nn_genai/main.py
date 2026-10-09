import asyncio
import json
import logging

from nn_genai.application.research.provenance_validator import (
    ProvenanceValidator,
)
from nn_genai.application.services.identity_service import IdentityService
from nn_genai.application.services.person_service import PersonService
from nn_genai.config import Settings
from nn_genai.infrastructure.agents.langchain_research_agent import (
    LangChainResearchAgent,
)
from nn_genai.infrastructure.clients.random_user_client import (
    RandomUserApiClient,
)
from nn_genai.infrastructure.llm.gemini_langchain_model import (
    create_research_model,
)
from nn_genai.infrastructure.llm.gemini_provider import GeminiLLMProvider
from nn_genai.infrastructure.search.tavily_search_provider import (
    TavilySearchProvider,
)
from nn_genai.observability.logging import configure_logging

logger = logging.getLogger(__name__)

FETCH_COUNT = 20
RESULT_COUNT = 5


async def main() -> None:
    settings = Settings.from_environment()
    configure_logging(settings.log_level)

    # Infrastructure adapters
    random_user_client = RandomUserApiClient(
        timeout=settings.http_timeout_seconds,
        max_attempts=settings.max_retry_attempts,
        retry_base_delay_seconds=settings.retry_base_delay_seconds,
    )

    identity_provider = GeminiLLMProvider(
        api_key=Settings.require_secret(
            settings.gemini_api_key,
            "GEMINI_API_KEY",
        ),
        model=settings.gemini_model,
        timeout_seconds=settings.http_timeout_seconds,
    )

    research_model = create_research_model(
        api_key=Settings.require_secret(
            settings.google_api_key,
            "GOOGLE_API_KEY",
        ),
        model_name=settings.gemini_model,
        timeout_seconds=settings.http_timeout_seconds,
    )

    search_provider = TavilySearchProvider(
        api_key=Settings.require_secret(
            settings.tavily_api_key,
            "TAVILY_API_KEY",
        ),
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.max_retry_attempts,
        retry_base_delay_seconds=settings.retry_base_delay_seconds,
    )

    # Application services
    person_service = PersonService()
    identity_service = IdentityService(identity_provider)
    provenance_validator = ProvenanceValidator()

    research_agent = LangChainResearchAgent(
        model=research_model,
        search_provider=search_provider,
        provenance_validator=provenance_validator,
        max_searches=settings.max_searches,
        recursion_limit=settings.agent_recursion_limit,
        timeout_seconds=settings.research_timeout_seconds,
    )

    # Exercises 1–5 - Printing for demo and verification purposes 
    people = await random_user_client.fetch_users(FETCH_COUNT)
    eligible_people = person_service.filter_people(people)
    selected_people = eligible_people[:RESULT_COUNT]

    logger.info(
        "people_selected fetched=%d eligible=%d selected=%d",
        len(people),
        len(eligible_people),
        len(selected_people),
    )

    results: list[dict[str, object]] = []

    for person in selected_people:
        logger.info("person_processing name=%s", person.full_name)

        identity = await identity_service.identify(person)
        research = await research_agent.research(identity.identity)

        results.append(
            {
                "input_person": person.model_dump(mode="json"),
                "identity": identity.model_dump(mode="json"),
                "research": research.model_dump(mode="json"),
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
