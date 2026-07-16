from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(_env_path), env_file_encoding="utf-8", extra="ignore")

    google_api_key: str = ""
    gemini_api_key: str = ""
    serp_api_key: str = ""
    openweather_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
