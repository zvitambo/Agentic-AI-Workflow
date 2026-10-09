class ResearchError(Exception):
    """Base exception exposed by the research application boundary."""


class ResearchTimeoutError(ResearchError):
    """The complete research operation exceeded its deadline."""


class SearchProviderError(ResearchError):
    """The configured search provider failed."""


class ModelProviderError(ResearchError):
    """The configured language-model provider failed."""


class AgentIterationLimitError(ResearchError):
    """The agent exceeded its controlled graph iteration limit."""


class SearchBudgetExceededError(ResearchError):
    """The agent attempted more searches than the request budget permits."""


class InvalidResearchOutputError(ResearchError):
    """The model failed to return the required structured output."""


class InvalidEvidenceReferenceError(ResearchError):
    """The model referenced evidence absent from the request ledger."""


class InsufficientEvidenceError(ResearchError):
    """The model claimed a conclusion without sufficient evidence."""
