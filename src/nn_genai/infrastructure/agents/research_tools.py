import hashlib
import logging
from collections.abc import Iterable

from langchain_core.tools import tool

from nn_genai.application.ports.search_provider import SearchProvider
from nn_genai.application.research.errors import SearchBudgetExceededError
from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.application.research.source_quality import classify_source_quality
from nn_genai.application.research.url_normalizer import normalize_url
from nn_genai.models.retrieved_evidence import RetrievedEvidence
from nn_genai.models.search_result import SearchResult

logger = logging.getLogger(__name__)


def rank_search_results(
    results: Iterable[SearchResult],
) -> list[SearchResult]:
    indexed_results = list(enumerate(results))
    ranked = sorted(
        indexed_results,
        key=lambda item: (
            -int(classify_source_quality(str(item[1].url))),
            item[0],
        ),
    )
    return [result for _, result in ranked]


def create_evidence_id(url: str) -> str:
    normalized_url = normalize_url(url)
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
    return f"evidence-{digest[:12]}"


def create_search_tool(
    search_provider: SearchProvider,
    evidence_ledger: EvidenceLedger,
    *,
    max_searches: int = 4,
):
    if max_searches < 1:
        raise ValueError("max_searches must be at least one")

    search_count = 0

    @tool("search_web")
    async def search_web(query: str) -> str:
        """Search the public web for factual evidence."""
        nonlocal search_count
        if search_count >= max_searches:
            raise SearchBudgetExceededError(
                f"Research search budget exhausted ({max_searches})"
            )

        search_count += 1
        logger.info("research_search_started search_number=%d", search_count)
        results = await search_provider.search(query)

        if not results:
            logger.info("research_search_completed result_count=0")
            return "No search results found."

        formatted_results: list[str] = []
        for index, result in enumerate(rank_search_results(results), start=1):
            normalized_url = normalize_url(str(result.url))
            evidence_id = create_evidence_id(normalized_url)
            evidence = RetrievedEvidence(
                evidence_id=evidence_id,
                title=result.title,
                url=normalized_url,
                snippet=result.snippet,
            )
            evidence_ledger.add(evidence)
            quality = classify_source_quality(str(evidence.url))
            formatted_results.append(
                f"{index}. {result.title}\n"
                f"Evidence ID: {evidence_id}\n"
                f"Source category: {quality.name.lower()}\n"
                f"URL: {normalized_url}\n"
                f"Snippet: {result.snippet}"
            )

        logger.info(
            "research_search_completed result_count=%d", len(formatted_results)
        )
        return "\n\n".join(formatted_results)

    return search_web
