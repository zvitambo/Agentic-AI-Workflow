from nn_genai.infrastructure.search.tavily_search_provider import (
    TavilySearchProvider,
)


def test_map_results() -> None:
    response = {
        "results": [
            {
                "title": "Albert Einstein",
                "url": "https://example.com/einstein",
                "content": "German-born theoretical physicist...",
            }
        ]
    }

    results = TavilySearchProvider._map_results(response)

    assert len(results) == 1
    assert results[0].title == "Albert Einstein"
    assert str(results[0].url) == (
        "https://example.com/einstein"
    )
    assert results[0].snippet == (
        "German-born theoretical physicist..."
    )


def test_map_empty_results() -> None:
    results = TavilySearchProvider._map_results({})

    assert results == []


def test_map_results_skips_entries_without_required_fields() -> None:
    response = {
        "results": [
            {
                "title": "Valid",
                "url": "https://example.com",
                "content": "Valid result",
            },
            {
                "title": "Missing URL",
                "content": "Invalid result",
            },
        ]
    }

    results = TavilySearchProvider._map_results(response)

    assert len(results) == 1
    assert results[0].title == "Valid"
