import asyncio
from datetime import date

from nn_genai.config import Settings, settings
from nn_genai.infrastructure.llm.gemini_provider import GeminiLLMProvider
from nn_genai.models.person import Person


async def main() -> None:
    provider = GeminiLLMProvider(
        api_key=Settings.require_secret(
            settings.gemini_api_key, "GEMINI_API_KEY"
        ),
        model=settings.gemini_model,
    )

    person = Person(
        first_name="Albert",
        last_name="Einstein",
        date_of_birth=date(1879, 3, 14),
        nationality="German",
        country="Germany",
        city="Ulm",
    )

    result = await provider.identify_person(person)

    print("Person:")
    print(person.full_name)

    print("\nIdentity:")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
