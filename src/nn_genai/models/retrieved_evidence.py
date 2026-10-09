
from enum import IntEnum

from pydantic import BaseModel, Field, HttpUrl


class SourceQuality(IntEnum):
    LOW = 1
    SECONDARY = 2
    AUTHORITATIVE = 3
    PRIMARY = 4


class RetrievedEvidence(BaseModel):
    evidence_id: str
    title: str
    url: HttpUrl
    snippet: str = Field(min_length=1)
    quality: SourceQuality = SourceQuality.SECONDARY
