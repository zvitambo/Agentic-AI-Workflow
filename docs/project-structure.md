# Project Structure

## Overview

The project uses a lightweight ports-and-adapters structure. Core workflows depend on application-defined interfaces rather than directly on Gemini, Tavily, LangChain, or RandomUser implementations.

This provides enough separation to isolate external services and probabilistic AI behavior without introducing unnecessary layers for a small project.

## Directory Tree

```text
agentic_ai_workflow/
├── .env.example
├── README.md
├── pyproject.toml
├── docs/
│   ├── decisions.md
│   └── project-structure.md
├── scripts/
│   ├── test_aiohttp_ssl.py
│   ├── test_gemini.py
│   ├── test_research_agent.py
│   └── test_tavily.py
├── src/nn_genai/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── application/
│   │   ├── ports/
│   │   │   ├── random_user_client.py
│   │   │   ├── research_agent.py
│   │   │   └── search_provider.py
│   │   ├── research/
│   │   │   ├── errors.py
│   │   │   ├── evidence_ledger.py
│   │   │   ├── provenance_validator.py
│   │   │   ├── source_quality.py
│   │   │   └── url_normalizer.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── identity_service.py
│   │       └── person_service.py
│   ├── infrastructure/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── langchain_research_agent.py
│   │   │   └── research_tools.py
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   └── random_user_client.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_langchain_model.py
│   │   │   ├── gemini_provider.py
│   │   │   ├── prompts.py
│   │   │   └── provider.py
│   │   └── search/
│   │       └── tavily_search_provider.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── person.py
│   │   ├── person_identity.py
│   │   ├── research_draft.py
│   │   ├── research_result.py
│   │   ├── research_status.py
│   │   ├── retrieved_evidence.py
│   │   └── search_result.py
│   └── observability/
│       ├── __init__.py
│       └── logging.py
└── tests/
    ├── __init__.py
    ├── test_identity_service.py
    ├── test_langchain_research_agent.py
    ├── test_operational_hardening.py
    ├── test_person_service.py
    ├── test_random_user_client.py
    ├── test_research_evidence.py
    ├── test_research_tools.py
    ├── test_tavily_search_provider.py
    └── fakes/
        ├── fake_research_model.py
        └── fake_search_provider.py
```

## Top-Level Files

### `.env.example`

Documents the environment variables required to run live integrations. It contains placeholders only; real credentials belong in an untracked `.env` file or a production secret store.

### `README.md`

Provides the main entry point for reviewers: setup, configuration, execution, testing, architecture, limitations, and operational behavior.

### `pyproject.toml`

Defines project metadata, runtime dependencies, development dependencies, packaging, and test configuration. It is the canonical dependency declaration.

## Documentation

### `docs/decisions.md`

Records important architectural decisions and their trade-offs, including the use of an agent, provider abstractions, structured output, timeouts, evidence validation, and the synchronous Tavily integration.

### `docs/project-structure.md`

Explains how responsibilities are divided across the repository and why the boundaries exist.

## Manual Integration Scripts

The `scripts/` directory contains live smoke tests and diagnostics. These scripts may require network access, API credentials, or local certificate configuration and are not part of the deterministic test suite.

- `test_aiohttp_ssl.py` diagnoses HTTPS and certificate-store connectivity.
- `test_gemini.py` verifies the live Gemini integration.
- `test_research_agent.py` exercises the complete research workflow.
- `test_tavily.py` verifies the live Tavily integration.

Keeping these checks separate prevents external service availability from making the automated test suite unreliable.

## Source Package

### `config.py`

Loads and validates runtime configuration. Configuration is kept outside business logic so timeouts, limits, model names, and credentials can vary by environment.

### `main.py`

Acts as the composition root. It constructs concrete infrastructure adapters, injects them into application services, and starts the workflow. Provider construction is centralized instead of being scattered across services.

## Application Layer

The application layer owns use-case orchestration, required capabilities, and deterministic research policies. It does not own vendor SDK configuration.

### `application/ports/`

Ports define the capabilities required by the application:

- `random_user_client.py` defines access to candidate-person data.
- `research_agent.py` defines the research capability expected by services.
- `search_provider.py` defines web-search behavior independently of Tavily.

These interfaces invert the dependency direction: application code depends on abstractions it owns, while infrastructure adapters implement those abstractions.

### `application/services/`

- `identity_service.py` coordinates identity resolution through an LLM provider and validates the returned identity.
- `person_service.py` coordinates person retrieval, identity resolution, research, and final result construction.

Services describe workflow rather than HTTP calls, SDK configuration, or agent-framework mechanics.

### `application/research/`

This package contains the deterministic safeguards around probabilistic research output:

- `errors.py` defines stable application-specific failures.
- `evidence_ledger.py` records evidence actually returned by searches during a research run.
- `provenance_validator.py` ensures final citations originate from retrieved evidence and support the submitted result.
- `source_quality.py` applies explicit source-quality rules and ranking heuristics.
- `url_normalizer.py` canonicalizes URLs before provenance comparison.

These controls are implemented in code because correctness requirements such as “do not cite a URL that was never retrieved” cannot be guaranteed by a prompt alone.

## Infrastructure Layer

The infrastructure layer contains implementations tied to external providers and frameworks. These are the most volatile parts of the system and are kept behind application-facing contracts.

### `infrastructure/clients/`

Contains the RandomUser HTTP adapter, including transport calls, response mapping, timeouts, and provider-error translation.

### `infrastructure/llm/`

- `provider.py` defines the LLM capability used for structured identity extraction.
- `gemini_provider.py` implements that capability with the Gemini SDK.
- `gemini_langchain_model.py` configures Gemini for LangChain agent execution.
- `prompts.py` stores model instructions separately from orchestration code.

The schema sent to Gemini guides generation, while local Pydantic validation decides whether the response is acceptable.

### `infrastructure/search/`

`tavily_search_provider.py` implements the search port with Tavily. It owns provider-specific request mapping, response mapping, timeout handling, retry policy, and exception translation.

The current adapter can run a synchronous SDK call in a worker thread to avoid blocking the asynchronous event loop. This is a deliberate minor-scale trade-off; a verified native asynchronous client would be preferable at higher concurrency.

### `infrastructure/agents/`

- `langchain_research_agent.py` contains LangChain/LangGraph orchestration, iteration limits, overall timeout handling, structured draft generation, and result validation.
- `research_tools.py` exposes the search port as an agent tool and records retrieved evidence.

Keeping agent-framework code here means the application service does not depend directly on LangChain or LangGraph.

## Models

The `models/` package contains typed data contracts shared across workflow boundaries:

- `person.py` represents a person returned by the external person source.
- `person_identity.py` represents validated identity information.
- `research_draft.py` represents the model-generated result before deterministic validation.
- `research_result.py` represents the validated final research result.
- `research_status.py` represents successful, failed, or inconclusive outcomes.
- `retrieved_evidence.py` represents evidence observed during tool execution.
- `search_result.py` represents a normalized provider search result.

Separating `ResearchDraft` from `ResearchResult` makes the trust boundary explicit: model output is provisional until provenance and evidence rules pass.

## Observability

`observability/logging.py` centralizes structured logging configuration. Operational events such as retries, failures, and timeouts can be recorded consistently without placing logging setup throughout the application.

## Tests

The `tests/` directory contains deterministic automated tests suitable for local execution and CI. External services are replaced with controlled fakes wherever possible.

- Service tests verify workflow coordination and failure propagation.
- Agent tests verify tool use, stopping behavior, structured output, and recursion handling.
- Evidence tests verify URL normalization, provenance, source quality, unsupported claims, fabricated URLs, and insufficient-evidence behavior.
- Operational-hardening tests verify timeouts, retries, limits, and error translation.
- Adapter tests verify provider response mapping independently of live services.

The `tests/fakes/` implementations provide predictable research-model and search-provider behavior. They allow edge cases to be tested without API keys, network access, cost, latency, or nondeterministic model responses.

## Dependency Direction

The intended dependency direction is:

```text
main.py
  -> infrastructure adapters
  -> application ports and services
  -> models
```

Application code does not import concrete Tavily, Gemini, or RandomUser implementations. Infrastructure code may depend inward on application ports and shared models.

## Design Rationale

The structure is organized around two principles:

1. **Responsibility:** orchestration, deterministic validation, provider integration, data contracts, and observability have different reasons to change.
2. **Volatility:** external providers and agent frameworks are more likely to change than the core use cases, so they remain at the infrastructure boundary.

This makes provider replacement and deterministic testing possible while keeping the design proportional to the assignment. The project deliberately avoids repositories, controllers, domain aggregates, and a dependency-injection framework because they would not currently solve a demonstrated requirement.

## Known Evolution Points

If the system grew beyond the simple project scope, likely changes would include:

- replacing thread-wrapped synchronous calls with verified native async clients;
- introducing persistent workflow and evidence storage;
- separating domain models from provider DTOs more strictly;
- adding dependency injection or application factories as composition grows;
- adding distributed rate limiting, queues, and durable retries;
- exporting metrics and traces to a production observability platform.

These extensions can be introduced without rewriting the core use cases because external behavior is already isolated behind ports.
