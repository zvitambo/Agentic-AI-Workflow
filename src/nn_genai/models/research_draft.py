from pydantic import BaseModel, Field, model_validator

from nn_genai.models.research_status import ResearchStatus


class EvidenceCitationDraft(BaseModel):
    evidence_id: str = Field(
        min_length=21,
        pattern=r"^evidence-[0-9a-f]{12}$",
        description=(
            "Exact Evidence ID returned by search_web. "
            "It must not be a URL, title, or invented identifier."
        ),
    )
    supporting_claim: str = Field(
        min_length=1,
        description=(
            "A claim supported by the snippet associated with this "
            "evidence ID."
        ),
    )


class ResearchDraft(BaseModel):
    person_name: str = Field(min_length=1)
    selected_work: str | None = None
    status: ResearchStatus
    reasoning: str = Field(min_length=1)
    citations: list[EvidenceCitationDraft] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_outcome(self) -> "ResearchDraft":
        if self.status is ResearchStatus.CONCLUSIVE:
            if not self.selected_work:
                raise ValueError("A conclusive result requires selected_work")
            if not self.citations:
                raise ValueError(
                    "A conclusive result requires retrieved evidence"
                )

        if self.status is ResearchStatus.INCONCLUSIVE:
            if self.selected_work is not None:
                raise ValueError(
                    "An inconclusive result must not select a work"
                )
            if self.confidence > 0.5:
                raise ValueError(
                    "An inconclusive result cannot have confidence above 0.5"
                )
        return self
