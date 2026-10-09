import asyncio
import logging
import time
import uuid

from langgraph.errors import GraphRecursionError

from nn_genai.infrastructure.agents.research_tools import create_search_tool
from nn_genai.application.research.provenance_validator import (
    ProvenanceValidator,
)
from nn_genai.application.ports.search_provider import SearchProvider
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.models.research_draft import ResearchDraft
from nn_genai.models.research_result import ResearchResult
from nn_genai.application.ports.research_agent import ResearchAgent
from langchain.agents.structured_output import ToolStrategy
from nn_genai.application.research.errors import (
    AgentIterationLimitError,
    InvalidResearchOutputError,
    ModelProviderError,
    ResearchTimeoutError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a research agent responsible for assessing a person's most
significant work or contribution.

You must produce an evidence-backed ResearchDraft using evidence retrieved
through the search_web tool.

Research process:

1. Always use search_web before producing the ResearchDraft.
2. First identify the person's major contributions.
3. Investigate the significance, impact, influence, or recognition of the
   strongest candidates.
4. Compare the candidates using retrieved evidence before selecting one.
5. Treat "most significant" as a reasoned, evidence-based assessment rather
   than an objective fact.
6. Avoid redundant searches.
7. Stop once the retrieved evidence is sufficient to support:
   - the identity of the selected contribution;
   - its significance or impact; and
   - its selection over the strongest plausible alternatives.
8. Prefer evidence from more than one independent source when available.
9. If the evidence does not support a comparative conclusion, search again
   while the search budget remains.
10. If the evidence remains insufficient, state that clearly instead of
    guessing or filling gaps with pretrained knowledge.

Source-selection rules:

1. Prefer primary or authoritative sources when they directly support the
   specific claim being made.
2. A source category is only a ranking signal. It does not prove that a source
   is relevant, accurate, or sufficient for a claim.
3. Evaluate whether the retrieved snippet actually supports the claim before
   citing it.
4. Use reputable secondary sources when they provide necessary historical
   interpretation, synthesis, or comparative judgment.
5. A source may support one factual claim without supporting the overall
   conclusion.
6. Use different sources when different parts of the reasoning require
   different evidence.
7. Do not select a source solely because its category appears stronger.

Evidence and citation rules:

1. search_web returns evidence entries containing an Evidence ID, title, URL,
   snippet, and source category.
2. Cite only evidence returned by search_web during the current research
   request.
3. Every evidence_id must be copied exactly from the value labelled
   "Evidence ID".
4. A valid evidence_id has the form:
   evidence- followed by 12 lowercase hexadecimal characters.
5. Never use a URL, title, result number, or source category as an evidence_id.
6. Never invent, modify, or reconstruct an Evidence ID.
7. Every supporting_claim must be directly supported by the snippet associated
   with its evidence_id.
8. Every important factual claim in reasoning must be supported by at least one
   citation.
9. Do not invent facts, sources, URLs, quotations, or evidence.
10. Do not use pretrained knowledge to replace missing retrieved evidence.

Insufficient-evidence behavior:

1. A conclusive result is permitted only when retrieved evidence supports:
   - the person's association with the selected contribution;
   - the contribution's significance, impact, influence, or recognition; and
   - the reasoned selection over the strongest plausible alternatives.
2. If one of these elements is unsupported, search again while the search
   budget remains.
3. If the search budget is exhausted and the evidence remains insufficient,
   return status="inconclusive".
4. For an inconclusive result:
   - set selected_work to null;
   - explain specifically what evidence is missing, conflicting, or inadequate;
   - include only citations whose claims are actually supported;
   - use a confidence score no greater than 0.5.
5. Never produce status="conclusive" by filling evidence gaps with pretrained
   knowledge.
6. Never describe an unsupported candidate as the selected work merely to
   complete the response.

Output requirements:

Return a ResearchDraft containing:

- person_name
- selected_work
- reasoning
- status: "conclusive" or "inconclusive"
- citations
  - evidence_id
  - supporting_claim
- confidence

The reasoning must:

- concisely explain why the selected work was chosen;
- distinguish retrieved facts from the comparative assessment;
- acknowledge material uncertainty or conflicting evidence; and
- avoid claims not supported by the cited snippets.

Confidence must be a number between 0 and 1 reflecting the strength,
relevance, independence, and completeness of the retrieved evidence.

Do not return source titles or URLs in the ResearchDraft. Trusted source
metadata will be validated and added by application code when it constructs
the final ResearchResult.
"""


class LangChainResearchAgent(ResearchAgent):
    """Concrete ResearchAgent implemented with LangChain."""

    def __init__(
        self,
        model: BaseChatModel,
        search_provider: SearchProvider,
        provenance_validator: ProvenanceValidator,
        max_searches: int = 4,
        recursion_limit: int = 12,
        timeout_seconds: float = 45.0,
    ) -> None:
        self._model = model
        self._search_provider = search_provider
        self._provenance_validator = provenance_validator
        if max_searches < 1 or recursion_limit < 1 or timeout_seconds <= 0:
            raise ValueError("limits must be greater than zero")
        self._max_searches = max_searches
        self._recursion_limit = recursion_limit
        self._timeout_seconds = timeout_seconds

    async def research(self, person_name: str) -> ResearchResult:
        normalized_name = person_name.strip()

        if not normalized_name:
            raise ValueError("'person name' cannot be empty")

        request_id = uuid.uuid4().hex
        started_at = time.monotonic()
        logger.info("research_started request_id=%s", request_id)

        # a new instance of the ledger for each research task
        # to ensure the evidence is scoped to the current research task only
        ledger = EvidenceLedger()
        search_tool = create_search_tool(
            search_provider=self._search_provider,
            evidence_ledger=ledger,
            max_searches=self._max_searches,
        )

        agent = create_agent(
            model=self._model,
            tools=[search_tool],
            system_prompt=SYSTEM_PROMPT,
            response_format=ToolStrategy(ResearchDraft),
        )

        try:
            result = await asyncio.wait_for(
                agent.ainvoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    f"Research {normalized_name} and determine their most "
                                    "significant work or contribution. Use search_web to "
                                    "gather evidence. In the final ResearchDraft, cite only "
                                    "the exact Evidence ID values returned by search_web; "
                                    "do not use URLs as evidence IDs."
                                ),
                            }
                        ]
                    },
                    config={"recursion_limit": self._recursion_limit},
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            logger.warning("research_timed_out request_id=%s", request_id)
            raise ResearchTimeoutError(
                f"Research exceeded {self._timeout_seconds} seconds"
            ) from error
        except GraphRecursionError as error:
            logger.warning(
                "research_iteration_limit request_id=%s", request_id)
            raise AgentIterationLimitError(
                f"Research exceeded {self._recursion_limit} graph steps"
            ) from error
        except Exception as error:
            raise ModelProviderError(
                "The research model request failed"
            ) from error

        structured_response = result.get("structured_response")

        if structured_response is None:
            raise InvalidResearchOutputError(
                "Research agent did not produce a structured response"
            )

        try:
            draft = ResearchDraft.model_validate(structured_response)
        except (TypeError, ValueError) as error:
            raise InvalidResearchOutputError(
                "Research agent returned an invalid ResearchDraft"
            ) from error

        # Exact validation and hydration boundary:
        research_result = self._provenance_validator.build_result(
            draft=draft,
            ledger=ledger,
        )
        logger.info(
            "research_completed request_id=%s status=%s source_count=%d "
            "latency_ms=%d",
            request_id,
            research_result.status.value,
            len(research_result.sources),
            int((time.monotonic() - started_at) * 1000),
        )
        return research_result
