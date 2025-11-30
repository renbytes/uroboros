import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    """
    Global Application Configuration.
    Loads variables from .env file or environment variables.
    Adheres to the 12-Factor App methodology.
    """
    
    # --- Project Info ---
    PROJECT_NAME: str = "uroboros-agent"
    ENVIRONMENT: str = Field(default="development", description="dev, staging, or prod")
    DEBUG: bool = False

    # --- LLM Provider Credentials ---
    # We use SecretStr to prevent keys from leaking in logs/tracebacks
    OPENAI_API_KEY: SecretStr
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    
    # --- Model Selection ---
    # Allows hot-swapping models via ENV vars without code changes
    ACTOR_MODEL: str = "gpt-4-turbo"
    ADVERSARY_MODEL: str = "gpt-4-turbo" 
    EVOLVER_MODEL: str = "gpt-4-turbo"

    # --- Infrastructure Credentials ---
    E2B_API_KEY: SecretStr = Field(..., description="API Key for E2B Sandboxes")
    GITHUB_TOKEN: Optional[SecretStr] = None # For fetching issues if needed
    
    # --- Vector DB (Memory) ---
    VECTOR_DB_PATH: str = "./data/chromadb"
    
    # --- Paths ---
    ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Allow extra env vars without throwing errors
    )

@lru_cache()
def get_settings() -> Settings:
    """
    Singleton pattern for settings.
    Cached to prevent re-reading .env from disk on every call.
    """
    return Settings()
