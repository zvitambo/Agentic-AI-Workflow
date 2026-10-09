from datetime import datetime
import asyncio
import logging

import httpx
from nn_genai.models.person import Person

logger = logging.getLogger(__name__)


class RandomUserClientError(Exception):
    """RandomUser transport or response failure."""


class RandomUserApiClient:
    BASE_URL = "https://randomuser.me/api/"

    def __init__(
        self,
        timeout: float = 5.0,
        max_attempts: int = 3,
        retry_base_delay_seconds: float = 0.5,
    ) -> None:
        if timeout <= 0 or max_attempts < 1:
            raise ValueError(
                "Timeout and retry limits must be greater than zero")
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._retry_base_delay_seconds = retry_base_delay_seconds

    async def fetch_users(self, count: int) -> list[Person]:
        if count < 1:
            raise ValueError("count must be at least one")

        for attempt in range(1, self._max_attempts + 1):
            try:
                # in production i would reuse one AsyncClient to benefit from connection pooling
                # preventing the overhead of creating a new TCP connection for every request
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        self.BASE_URL,
                        params={"results": count},
                    )
                    response.raise_for_status()
                    payload = response.json()
                break
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                if attempt == self._max_attempts:
                    raise RandomUserClientError(
                        "RandomUser request failed after transient retries"
                    ) from error
                logger.warning(
                    "random_user_retry attempt=%d max_attempts=%d",
                    attempt,
                    self._max_attempts,
                )
                await asyncio.sleep(
                    self._retry_base_delay_seconds * (2 ** (attempt - 1))
                )
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429 or (
                    500 <= error.response.status_code < 600
                ):
                    if attempt < self._max_attempts:
                        await asyncio.sleep(
                            self._retry_base_delay_seconds *
                            (2 ** (attempt - 1))
                        )
                        continue
                raise RandomUserClientError(
                    "RandomUser request failed") from error
            except (TypeError, ValueError) as error:
                raise RandomUserClientError(
                    "RandomUser returned invalid JSON"
                ) from error

        results = payload.get("results")

        if not isinstance(results, list):
            raise RandomUserClientError(
                "RandomUser API returned an invalid results payload")

        return [
            self._to_person(user)
            for user in results
        ]

    @staticmethod
    def _to_person(user: dict) -> Person:
        name = user["name"]
        dob = user["dob"]
        location = user.get("location", {})

        date_of_birth = datetime.fromisoformat(
            dob["date"].replace("Z", "+00:00")
        ).date()

        return Person(
            first_name=name["first"],
            last_name=name["last"],
            date_of_birth=date_of_birth,
            nationality=user.get("nat"),
            country=location.get("country"),
            city=location.get("city"),
        )
