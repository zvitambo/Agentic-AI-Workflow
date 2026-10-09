
from pydantic import BaseModel, Field, HttpUrl

from nn_genai.models.research_status import ResearchStatus


class ResearchSource(BaseModel):
    title: str
    url: HttpUrl
    supporting_claim: str


class ResearchResult(BaseModel):
    person_name: str = Field(min_length=1)
    selected_work: str | None = None
    reasoning: str = Field(min_length=1)
    status: ResearchStatus
    sources: list[ResearchSource] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
