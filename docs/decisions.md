# Architecture Decision Record

This document captures the main architectural decisions behind the project and, more importantly, why they were made.

The decisions are specific to this project and are intended to keep the implementation simple while still leaving sensible boundaries between the application logic and external services.

## ADR-001 — Keep external services behind interfaces

**Decision**

Define application-level interfaces for RandomUser, web search, and research, with the actual integrations implemented separately under `clients/` or `infrastructure/`.

**Why**

The application code should not depend directly on vendor SDKs. It also makes testing much easier because the real services can be replaced with simple fakes.

**Trade-off**

There is a little more structure than the size of the project strictly requires, but it gives the external integrations clear boundaries and makes them easier to replace.

## ADR-002 — Validate and normalize data at the boundaries

**Decision**

Convert external data into the types used by the application as soon as it enters the system. For example, RandomUser's timestamp is converted to a Python `date`, and only the fields required by the application are mapped.

Model responses are also validated before being passed further into the application.

**Why**

External APIs and LLMs should not be treated as trusted application data. Keeping the conversion and validation at the boundary makes the rest of the application simpler and safer.

## ADR-003 — Interpret "after 2000" 

**Decision**

Keep people born in 2000 or earlier and exclude people born after 2000.

In other words:

```text
birth year <= 2000 → included
birth year > 2000  → excluded
```

**Why**

This follows the wording of the requirement: "born after the year 2000."

## ADR-004 — Keep filtering separate from formatting

**Decision**

`PersonService` works with typed `Person` objects and performs the filtering before converting them into the output format.

**Why**

Filtering is application logic, while formatting is presentation logic. Keeping them separate also means the same `Person` objects can be passed to the identity-resolution step without having to parse formatted strings again.

## ADR-005 — Use structured output from Gemini

**Decision**

Gemini is accessed through an `LLMProvider` interface. The model is asked to return schema-constrained JSON, which is then validated locally as a `PersonIdentity` model.

Invalid or unusable model responses are converted into a `ModelProviderError`.

**Why**

Structured output makes the integration much more predictable than relying on free-form text. The Pydantic validation step is the final check before model data enters the application.

The rest of the application therefore does not need to know anything about Gemini's raw response format.

**Trade-off**

The Gemini adapter contains some provider-specific logic, but this keeps that complexity out of the application services.

## ADR-006 — Keep identity resolution focused on one person

**Decision**

`IdentityService.identify()` handles one person at a time. Any batching or concurrency decisions are left to the caller.

**Why**

This gives the service a small and clear contract and avoids mixing provider-specific concurrency decisions into the identity-resolution logic.

**Trade-off**

The current entry point does not batch identity requests. For a maximum of five people, sequential calls are a reasonable starting point, particularly when working with free-tier API limits. If higher throughput is needed later, bounded concurrency can be added at the orchestration level.

## ADR-007 — Use an agent where the problem is genuinely open-ended

**Decision**

Use a LangChain agent for researching a person's contribution, while keeping retrieval, filtering, and identity resolution deterministic.

**Why**

The research step is different from the rest of the application. The agent may need to search for several candidates, compare information, and decide whether another search is worthwhile.

That kind of iterative research is where an agent provides value.

**Alternative**

A fixed `search → generate` pipeline would be simpler and more predictable, but it would also make the research process less flexible.

**Trade-off**

Agents introduce additional latency and non-deterministic behavior, so the research flow needs explicit limits around searches, recursion, time, output structure, and evidence.

## ADR-008 — Give the agent a single, focused tool

**Decision**

The agent only has access to `search_web`, which is backed by the application's `SearchProvider` interface.

**Why**

The research task requires web search, but it does not require the agent to perform other actions.

Keeping the tool surface small reduces the chance of unexpected behavior and makes the agent easier to test and reason about.

## ADR-009 — Validate research provenance after the agent finishes

**Decision**

Search results are normalized and stored in a request-scoped `EvidenceLedger`. Each result receives a deterministic evidence ID.

The model returns evidence IDs along with its claims, rather than being allowed to provide the final source metadata itself.

`ProvenanceValidator.build_result()` checks those IDs against the ledger and builds the final source information from the results that were actually retrieved.

**Why**

A prompt telling an LLM not to invent citations is not enough. The application should verify this independently.

The final response should only contain URLs that were actually returned by the search process for that request.

**Trade-off**

This verifies where the evidence came from, but it does not fully prove that every claim is supported by the cited text. A stronger implementation could add semantic claim-to-source verification later.

## ADR-010 — Treat source quality as a ranking signal

**Decision**

Prefer recognized authoritative domains when ordering search results, while preserving the provider's ordering within the same category.

The agent is also asked to consider whether the returned snippet actually supports the claim it is making.

**Why**

Primary and institutional sources are generally preferable, but the domain alone does not tell us whether a particular result is relevant or whether the claim is actually supported.

**Trade-off**

Domain classification is deterministic and easy to explain, but it remains a heuristic rather than a guarantee of source quality.

## ADR-011 — Allow the research process to say "inconclusive"

**Decision**

Research can return:

```text
status = "inconclusive"
selected_work = null
```

along with an explanation of what evidence was missing or conflicting. In this case, confidence cannot be greater than `0.5`.

**Why**

Sometimes the available sources simply aren't enough to confidently establish the person's association, the impact of their work, and why it should be selected over other contributions.

In that situation, returning an uncertain result is preferable to filling the gaps with information from the model's general knowledge.

**Enforcement**

The response schema enforces the relationship between status and confidence, while provenance validation ensures that referenced evidence actually exists. The research prompt also tells the agent when an inconclusive result is appropriate.

## ADR-012 — Use separate timeouts for individual calls and the whole research flow

**Decision**

External calls have their own timeout, while the complete research operation has a separate overall deadline.

**Why**

A single provider call should not be allowed to hang indefinitely, but having individual call timeouts alone is not enough. A workflow involving several searches could still run for too long.

The outer deadline provides a limit for the complete operation.

**Trade-off**

The two levels need to be configured sensibly. Retries, backoff, multiple searches, and model calls all contribute to the overall time even if each individual call stays within its own timeout.

## ADR-013 — Retry only failures that are likely to be temporary

**Decision**

The Tavily integration retries `TimeoutError`, `ConnectionError`, and `OSError` with bounded exponential backoff.

Other exceptions are allowed to fail immediately.

Gemini requests are not retried in the current implementation.

**Why**

Retries are useful for temporary network problems, but retrying every exception can make things worse. Authentication errors, invalid requests, validation failures, and programming errors are unlikely to be fixed by trying the same request again.

**Trade-off**

Some provider-specific transient errors, such as rate-limit exceptions, are not currently handled by the retry logic. A production implementation could map the SDK's specific error types and respect any retry information returned by the provider.

## ADR-014 — Run Tavily's synchronous SDK call outside the event loop

**Decision**

The Tavily SDK's synchronous `invoke()` method is called through `asyncio.to_thread()` behind the application's asynchronous `SearchProvider` interface.

**Why**

The rest of the application uses async I/O, but the available Tavily integration is synchronous. Running it in a worker thread prevents the blocking call from blocking the asyncio event loop.

**Trade-off**

Cancelling the coroutine stops waiting for the result, but it does not reliably stop the underlying worker thread. Each concurrent request also consumes a thread.

A native async Tavily integration would be a better option if this component needed to handle high concurrency.

## ADR-015 — Put multiple limits around agent execution

**Decision**

Agent execution is bounded in three ways:

1. Maximum number of searches
2. LangGraph recursion limit
3. Overall research timeout

**Why**

Each limit protects against a different failure mode.

* The search limit controls tool usage and cost.
* The recursion limit protects against unexpected agent loops.
* The timeout controls overall response latency.

If one of these limits is reached, the application treats it as an error rather than returning a partial research result.

## ADR-016 — Keep automated tests separate from live integration checks

**Decision**

Mocked and fake-backed tests live under `tests/`.

Scripts that make real network calls are kept under `scripts/`.

**Why**

The automated tests need to be repeatable and should not depend on whether an external provider happens to be available.

The scripts serve a different purpose: they are useful for checking that the local environment can actually reach and authenticate against the external services.

## ADR-017 — Log useful metadata without logging sensitive data

**Decision**

Application logs contain operational information such as:

* request IDs
* result counts
* status
* latency
* retry attempts
* timeout events
* agent iteration-limit failures

API keys, prompts, full model responses, and unnecessary personal information are not logged.

**Why**

The logs should provide enough information to understand what happened without becoming another place where credentials or sensitive data can leak.

**Trade-off**

A production deployment would likely add metrics and distributed tracing, as well as more detailed cost/token monitoring and potentially an audit trail. Those are separate concerns from the core simple project implementation.
