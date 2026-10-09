from langchain_google_genai import ChatGoogleGenerativeAI


def create_research_model(
    api_key: str,
    model_name: str = "gemini-3.6-flash",
    timeout_seconds: float = 30.0,
) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        timeout=timeout_seconds,
    )
