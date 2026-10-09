# Agentic AI Workflow

This project is a small, production-minded implementation of a Agentic Workflow demostrating.

The application retrieves people from RandomUser, applies the required filtering, uses Gemini to resolve identities, and then uses a LangChain agent with Tavily to research a person's most significant contribution.

The goal was to keep the implementation simple while still paying attention to the areas that tend to cause problems in real applications: external API calls, model output, retries and timeouts, agent loops, configuration, secret handling, and making sure research results can be traced back to the sources that were actually retrieved.

## Requirements

* Python 3.11 or newer
* A Gemini API key for the live identity-resolution and research flows
* A Tavily API key for live search and research

The automated test suite does not require API keys or network access.

## Setup

From the project root, create a virtual environment and install the project with its development dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

The project dependencies are defined in `pyproject.toml`, which is the source of truth. There is no separate `requirements.txt` to maintain.

## Configuration

Create a local `.env` file with the credentials and settings needed for the commands you want to run:

```dotenv
GEMINI_API_KEY=
GOOGLE_API_KEY=
TAVILY_API_KEY=

GEMINI_MODEL=gemini-3.6-flash

HTTP_TIMEOUT_SECONDS=10
RESEARCH_TIMEOUT_SECONDS=45

MAX_RETRY_ATTEMPTS=3
RETRY_BASE_DELAY_SECONDS=0.5

MAX_SEARCHES=4
AGENT_RECURSION_LIMIT=12

LOG_LEVEL=INFO
```

`GEMINI_API_KEY` is used by the direct Gemini integration, while `GOOGLE_API_KEY` is used by the LangChain Gemini integration. They can contain the same key, but both variables are kept because the underlying libraries expect different environment variable names.

Do not commit `.env` or put real API keys in source code, tests, documentation, logs, or the submission archive.

If a key is accidentally exposed, it should be rotated.

## Running the tests

The deterministic test suite can be run with:

```bash
python -m pytest -v
python -m pip check
```

The tests use mocks and fakes rather than calling the real external services.

They cover things such as:

* application behavior and error handling
* HTTP timeouts and retries
* search limits
* structured Gemini output
* URL normalization
* evidence provenance
* conclusive and inconclusive research results

This keeps the CI/test suite fast and predictable and avoids depending on external APIs.

## Running the application

The main entry point demonstrates the RandomUser retrieval and filtering flow:

```bash
python -m nn_genai.main
```

## Manual integration checks

The scripts in `scripts/` are intended for manually testing the real external integrations. They are separate from the deterministic pytest suite.

```bash
python scripts/test_aiohttp_ssl.py
python scripts/test_gemini.py
python scripts/test_tavily.py
python scripts/test_research_agent.py
```

Only run the scripts for services for which you have configured credentials.

Because these tests use live services, they can fail due to provider availability, rate limits, network restrictions, or local TLS configuration. For that reason, they are not used as deterministic CI tests.

## Architecture

The project uses a ports-and-adapters approach to keep the application logic separate from external services.

At a high level:

* **Application ports** define the interfaces for RandomUser, search, and research.
* **Infrastructure adapters** handle the actual HTTP, Gemini, Tavily, and LangChain integrations.
* **Pydantic models** validate data coming from external APIs and LLMs.
* **Application services** handle filtering, formatting, and identity-resolution logic.
* **Evidence ledger** keeps track of the search results retrieved during the current research request.
* **Provenance validation** makes sure that evidence referenced by the model actually exists in that ledger before it is included in the final response.

The agent is responsible for deciding what searches are useful, but it does not have unlimited freedom. Its behavior is constrained by a maximum search budget, a LangGraph recursion limit, an overall research timeout, structured output validation, and citation/provenance validation.

The concrete project structure is documented in [`docs/project-structure.md`](docs/project-structure.md) and [`docs/decisions.md`](docs/decisions.md) for the main trade-offs.

## Evidence and failure handling

One of the important design decisions in the research flow is that a conclusive answer must be backed by evidence retrieved during the current request.

The model cannot simply invent an evidence ID or refer to a source that was not actually returned by the search tool. If it does, the provenance validation step rejects it.

Similarly, if the available search results are not enough to establish the person's association, the impact of their contribution, and why it should be considered the most significant contribution, the agent should return an `inconclusive` result rather than trying to fill in the missing information from its general knowledge.

Source-category ranking is used as a heuristic to prefer certain types of sources, but it is not treated as proof that a source is relevant or that a particular claim is supported by it.

The current implementation validates provenance deterministically. More advanced semantic claim verification would be a natural next step for a production system.

## Timeouts, retries, and operational limits

The external integrations are deliberately bounded so that a slow or failing provider does not hang the entire application.

* RandomUser and Gemini use asynchronous I/O.
* Tavily's synchronous `invoke` call is executed in a worker thread so it does not block the main event loop.
* Tavily has a per-attempt timeout and bounded exponential backoff for selected transient failures.
* The research flow has its own overall timeout.
* The agent has a maximum number of searches it can perform.
* LangGraph's recursion limit provides another safeguard against an agent getting stuck in an unexpectedly long loop.

One limitation of the current implementation is that cancelling `asyncio.to_thread()` stops waiting for the result, but it does not reliably terminate the underlying thread itself.

For a high-concurrency production environment, I would prefer a native asynchronous Tavily transport so that cancellation and resource management can be handled more cleanly.

## Submission hygiene

The final submission should not contain generated files, virtual environments, caches, or secrets.

The following should be excluded:

```text
.env
.git/
.venv/
*.egg-info/
__pycache__/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
```

The intention is to keep the submission small and focused while demonstrating the engineering practices I would expect around an AI application that interacts with external APIs and autonomous model-driven workflows.

