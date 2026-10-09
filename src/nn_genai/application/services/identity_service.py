from nn_genai.infrastructure.llm.provider import LLMProvider
from nn_genai.models.person import Person
from nn_genai.models.person_identity import PersonIdentity


class IdentityService:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider

    async def identify(
        self,
        person: Person,
    ) -> PersonIdentity:
        return await self._llm_provider.identify_person(person)
