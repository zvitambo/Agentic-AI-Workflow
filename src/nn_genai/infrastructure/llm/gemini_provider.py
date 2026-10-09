import asyncio

from google import genai

from nn_genai.infrastructure.llm.prompts import (
    SYSTEM_PROMPT,
    build_identity_prompt,
)
from nn_genai.models.person import Person
from nn_genai.models.person_identity import PersonIdentity
from nn_genai.application.research.errors import ModelProviderError


class GeminiLLMProvider:
    """Gemini implementation of the LLMProvider port."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def identify_person(
        self,
        person: Person,
    ) -> PersonIdentity:
        prompt = build_identity_prompt(
            name=person.full_name,
            nationality=person.nationality,
            country=person.country,
            city=person.city,
        )

        try:
            # created an awaitable with a deadline "self._timeout_seconds,"
            # otherwise we could call  self._client.aio.interactions.create directly 
            # and not handle timeout errors 
            interaction = await asyncio.wait_for(
                self._client.aio.interactions.create(
                    model=self._model,
                    input=prompt,
                    system_instruction=SYSTEM_PROMPT,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": PersonIdentity.model_json_schema(),
                    },
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            raise ModelProviderError("Gemini request timed out") from error
        except Exception as error:
            raise ModelProviderError("Gemini request failed") from error

        if not interaction.output_text:
            raise ModelProviderError("Gemini returned an empty response")

        try:
            return PersonIdentity.model_validate_json(interaction.output_text)
        except ValueError as error:
            raise ModelProviderError(
                "Gemini returned invalid structured output"
            ) from error
