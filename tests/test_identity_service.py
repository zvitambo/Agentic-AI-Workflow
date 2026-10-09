

from datetime import date

import pytest

from nn_genai.models.person import Person
from nn_genai.models.person_identity import PersonIdentity
from nn_genai.application.services.identity_service import IdentityService


class FakeLLMProvider:
    async def identify_person(
        self,
        person: Person,
    ) -> PersonIdentity:
        return PersonIdentity(
            name=person.full_name,
            identity="Test identity",
            occupation="Test occupation",
            known_for=["Test contribution"],
            confidence=0.9,
        )


@pytest.mark.asyncio
async def test_identity_service_delegates_to_provider():
    person = Person(
        first_name="Albert",
        last_name="Einstein",
        date_of_birth=date(1879, 3, 14),
    )

    service = IdentityService(FakeLLMProvider())

    result = await service.identify(person)

    assert result.name == "Albert Einstein"
    assert result.confidence == 0.9
