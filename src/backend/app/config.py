import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./screening.db"
    GROQ_API_KEY: Optional[str] = None
    GITHUB_PAT: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/calendar/callback"
    ENCRYPTION_KEY: str = "vI9Tf43H2Bv9Zk-d8o4q_L9s1cM0G-H-J4kL3pP7qR4="
    MAILTRAP_TOKEN: Optional[str] = None

    # Load from .env file if it exists
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
