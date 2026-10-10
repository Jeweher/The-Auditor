"""
File: app/core/config.py
Folder: backend/app/core
Purpose: Single source of truth for all environment-driven configuration.
         Every other module reads settings from here — never from os.environ
         directly — so config stays testable and swappable per environment.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "TISAXAI"
    ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=True)

    # --- Postgres ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://tisaxai:tisaxai@localhost:5432/tisaxai"
    )

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # --- Vector Store (ChromaDB) ---
    CHROMA_HOST: str = Field(default="chromadb")
    CHROMA_PORT: int = Field(default=8000)
    DEFAULT_KB_COLLECTION_NAME: str = Field(default="tisax_kb_final")

    # --- Embeddings ---
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/LaBSE")

    # --- LLM ---
    LLM_PROVIDER: str = Field(default="anthropic")  # anthropic | gemini | ollama
    LLM_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="claude-sonnet-4-6")
    LLM_MAX_TOKENS: int = Field(default=2000)

    # --- Ollama (local finetuned model) ---
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="tisax-qwen")

    # --- CORS ---
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- File storage ---
    EVIDENCE_STORAGE_PATH: str = Field(default="./data/evidence")
    MAX_UPLOAD_SIZE_MB: int = Field(default=25)

    STORAGE_PROVIDER: str = "local"
    TESSERACT_CMD: str = ""
    ADMIN_BOOTSTRAP_EMAIL: str = ""

    # --- Email (Resend) ---
    RESEND_API_KEY: str = Field(default="")
    RESEND_FROM_EMAIL: str = Field(default="onboarding@resend.dev")
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = Field(default=15)
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = Field(default=5)

        # --- Security ---
    ENCRYPTION_KEY: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import and call this, don't instantiate Settings() elsewhere."""
    return Settings()
