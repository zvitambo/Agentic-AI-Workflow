import asyncio
import logging

from langchain_tavily import TavilySearch
from nn_genai.application.research.errors import SearchProviderError
from nn_genai.models.search_result import SearchResult

logger = logging.getLogger(__name__)


class TavilySearchProvider:
    """Tavily implementation of the SearchProvider port."""

    def __init__(
        self,
        api_key: str,
        max_results: int = 5,
        timeout_seconds: float = 10.0,
        max_attempts: int = 3,
        retry_base_delay_seconds: float = 0.5,
    ) -> None:
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required")

        if timeout_seconds <= 0 or max_attempts < 1:
            raise ValueError(
                "Timeout and retry limits must be greater than zero")
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._search = TavilySearch(
            max_results=max_results,
            topic="general",
            search_depth="basic",
            tavily_api_key=api_key,
        )

    async def search(self, query: str) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("Search query cannot be empty")

        for attempt in range(1, self._max_attempts + 1):
            try:

                # The application exposes an async search port, 
                # Tavily’s synchronous SDK entry point because it was the simplest integration to validate within the time limit.
                # Tavily's adapter is calling a synchronous SDK method.
                # Calling it directly would block the event loop, 
                # so I isolated it in a worker thread with asyncio.to_thread
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._search.invoke,
                        {"query": query},
                    ),
                    timeout=self._timeout_seconds,
                )
                return self._map_results(response)
            except TimeoutError as error:
                if attempt == self._max_attempts:
                    raise SearchProviderError(
                        f"Tavily search timed out after "
                        f"{self._max_attempts} attempts"
                    ) from error

                # calculates an exponential backoff delay before 
                # retrying a failed request:
                delay = self._retry_base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "tavily_timeout attempt=%d max_attempts=%d delay_seconds=%.1f",
                    attempt,
                    self._max_attempts,
                    delay,
                )
                await asyncio.sleep(delay)
            except (ConnectionError, OSError) as error:
                if attempt == self._max_attempts:
                    raise SearchProviderError(
                        "Tavily search failed after connection retries"
                    ) from error

                delay = self._retry_base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "tavily_connection_retry attempt=%d max_attempts=%d",
                    attempt,
                    self._max_attempts,
                )
                await asyncio.sleep(delay)
            except SearchProviderError:
                raise
            except Exception as error:
                raise SearchProviderError("Tavily search failed") from error

        raise AssertionError("Retry loop terminated unexpectedly")

    @staticmethod
    def _map_results(response: dict) -> list[SearchResult]:
        if "error" in response:
            raise SearchProviderError(
                f"Tavily search failed: {response['error']}"
            )

        results = response.get("results", [])

        return [
            SearchResult(
                title=result["title"],
                url=result["url"],
                snippet=result.get("content", ""),
            )
            for result in results
            if result.get("title") and result.get("url")
        ]
