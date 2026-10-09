
from typing import Protocol

from nn_genai.models.research_result import ResearchResult


class ResearchAgent(Protocol):
    async def research(self, person_name: str) -> ResearchResult:
        """Research the person's most significant work."""
        ...
