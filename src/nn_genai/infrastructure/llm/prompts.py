

SYSTEM_PROMPT = """
You are a factual identity research assistant.

Your task is to identify a person using the supplied information.

Important rules:
- Do not invent facts.
- Do not assume that a name uniquely identifies a person.
- If the available information is insufficient to identify the person,
  explicitly state that the identity is uncertain.
- Only provide information you have reasonable confidence in.
- Keep the response concise.
- Return only the requested structured output.

""".strip()


def build_identity_prompt(
    name: str,
    nationality: str | None = None,
    country: str | None = None,
    city: str | None = None,
) -> str:
    return f"""
                Identify this person:

                Name: {name}
                Nationality: {nationality or "Unknown"}
                Country: {country or "Unknown"}
                City: {city or "Unknown"}

                Determine:
                1. Who this person most likely is.
                2. Their primary occupation or role.
                3. What they are best known for.
                4. How confident you are in the identification.

                If the information is insufficient or the name is ambiguous,
                do not guess. Indicate that the identity could not be reliably determined.
                """.strip()
