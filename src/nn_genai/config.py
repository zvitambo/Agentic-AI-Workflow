import os
from dataclasses import dataclass

from dotenv import load_dotenv
from pydantic import SecretStr


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be at least one")
    return value


@dataclass(frozen=True)
class Settings:
    gemini_api_key: SecretStr
    google_api_key: SecretStr
    tavily_api_key: SecretStr
    gemini_model: str
    http_timeout_seconds: float
    research_timeout_seconds: float
    max_retry_attempts: int
    retry_base_delay_seconds: float
    max_searches: int
    agent_recursion_limit: int
    log_level: str

    @classmethod
    def from_environment(cls, *, load_env_file: bool = True) -> "Settings":
        if load_env_file:
            load_dotenv()

        return cls(
            gemini_api_key=SecretStr(os.getenv("GEMINI_API_KEY", "")),
            google_api_key=SecretStr(os.getenv("GOOGLE_API_KEY", "")),
            tavily_api_key=SecretStr(os.getenv("TAVILY_API_KEY", "")),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            http_timeout_seconds=_positive_float(
                "HTTP_TIMEOUT_SECONDS", 60.0),  # 30.0 for demo purposes - Otherwise 10.0 is realistic in a live env
            research_timeout_seconds=_positive_float(
                "RESEARCH_TIMEOUT_SECONDS", 120.0  # 120.0 for demo purposes - Otherwise 45.0 is realistic in a live env
            ),
            max_retry_attempts=_positive_int("MAX_RETRY_ATTEMPTS", 3),
            retry_base_delay_seconds=_positive_float(
                "RETRY_BASE_DELAY_SECONDS", 0.5
            ),
            max_searches=_positive_int("MAX_SEARCHES", 4),
            agent_recursion_limit=_positive_int("AGENT_RECURSION_LIMIT", 12),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    @staticmethod
    def require_secret(secret: SecretStr, name: str) -> str:
        value = secret.get_secret_value()
        if not value:
            raise ValueError(f"{name} is required")
        return value


settings = Settings.from_environment()
