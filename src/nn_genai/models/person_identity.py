from pydantic import BaseModel, Field

class PersonIdentity(BaseModel):
    name: str
    identity: str
    occupation: str | None = None
    known_for: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
