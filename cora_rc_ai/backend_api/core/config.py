"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str = "cora-secret-change-in-production"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "postgresql://postgres:<<DB_PASSWORD>>@localhost:5432/cora"
    DOCUMENT_UPLOAD_DIR: str = "uploads/regulations"

    # Agentic backend
    AGENTIC_BACKEND_URL: str = "http://localhost:8080"

    # Redis (optional for task queues)
    REDIS_URL: str = "redis://localhost:6379"

    # Observability — LangSmith
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "cora-rc-ai"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_TRACING_V2: str = "true"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
