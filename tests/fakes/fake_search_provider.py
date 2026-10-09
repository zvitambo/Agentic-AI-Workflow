from nn_genai.models.search_result import SearchResult


class FakeSearchProvider:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return self._results
