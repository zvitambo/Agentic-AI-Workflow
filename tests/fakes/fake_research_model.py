from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from nn_genai.infrastructure.agents.research_tools import create_evidence_id


EINSTEIN_EVIDENCE_ID = create_evidence_id(
    "https://example.com/einstein"
)


class FakeResearchModel(BaseChatModel):
    """Deterministic model for testing LangChain agent orchestration."""

    bound_tools: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "fake-research-model"

    def bind_tools(
        self,
        tools: Sequence[BaseTool | dict[str, Any]],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable:
        self.bound_tools = list(tools)
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self._has_search_result(messages):
            message = self._create_search_call()
        else:
            message = self._create_research_draft_call(
                tool_name=self._structured_output_tool_name()
            )

        return ChatResult(
            generations=[ChatGeneration(message=message)]
        )

    def _structured_output_tool_name(self) -> str:
        names = [
            self._get_tool_name(bound_tool)
            for bound_tool in self.bound_tools
        ]

        candidates = [
            name
            for name in names
            if name and name != "search_web"
        ]

        if len(candidates) != 1:
            raise AssertionError(
                "Expected exactly one structured-output tool, "
                f"but found bound tools: {names}"
            )

        return candidates[0]

    @staticmethod
    def _get_tool_name(tool: BaseTool | dict[str, Any]) -> str | None:
        if isinstance(tool, BaseTool):
            return tool.name

        if "name" in tool:
            return str(tool["name"])

        function = tool.get("function")
        if isinstance(function, dict) and "name" in function:
            return str(function["name"])

        return None

    @staticmethod
    def _create_search_call() -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_web",
                    "args": {
                        "query": (
                            "Albert Einstein most significant "
                            "scientific contribution"
                        ),
                    },
                    "id": "search-call-1",
                    "type": "tool_call",
                }
            ],
        )

    @staticmethod
    def _create_research_draft_call(
        tool_name: str,
    ) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": {
                        "person_name": "Albert Einstein",
                        "selected_work": "Theory of relativity",
                        # Use your actual valid enum value.
                        "status": "conclusive",
                        "reasoning": (
                            "Relativity fundamentally changed our understanding "
                            "of space, time, gravity, and modern physics."
                        ),
                        "citations": [
                            {
                                "evidence_id": EINSTEIN_EVIDENCE_ID,
                                "supporting_claim": (
                                    "Einstein developed the theories of special "
                                    "and general relativity."
                                ),
                            }
                        ],
                        "confidence": 0.95,
                    },
                    "id": "structured-output-1",
                    "type": "tool_call",
                }
            ],
        )

    @staticmethod
    def _has_search_result(
        messages: list[BaseMessage],
    ) -> bool:
        return any(
            isinstance(message, ToolMessage)
            and message.name == "search_web"
            for message in messages
        )
