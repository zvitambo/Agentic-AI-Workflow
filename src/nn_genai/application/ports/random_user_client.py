
from typing import Protocol

from nn_genai.models.person import Person


class RandomUserClient(Protocol):
    async def fetch_users(self, count: int) -> list[Person]:
        ...
