from typing import Protocol

from nn_genai.models.search_result import SearchResult


class SearchProvider(Protocol):
    async def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        ...
