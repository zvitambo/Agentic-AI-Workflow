
from typing import Protocol

from nn_genai.models.person import Person
from nn_genai.models.person_identity import PersonIdentity


class LLMProvider(Protocol):
    async def identify_person(
        self,
        person: Person,
    ) -> PersonIdentity:
        ...
