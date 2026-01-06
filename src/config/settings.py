"""Configuration settings using Pydantic."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Pinecone
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_environment: str = Field(default="us-east-1", description="Pinecone environment")
    pinecone_index_name: str = Field(default="devdocs-index", description="Pinecone index name")

    # Paths
    data_dir: Path = Field(default=Path("data/runs"), description="Data directory")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Embedding
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )
    embedding_dimensions: int = Field(default=1536, description="Embedding dimensions")

    # Chunking
    default_chunk_size: int = Field(default=1000, description="Default chunk size in tokens")
    default_overlap: int = Field(default=200, description="Default chunk overlap in tokens")

    # Crawling
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    delay_between_requests: float = Field(
        default=0.5,
        description="Delay between requests in seconds",
    )


def load_framework_config() -> dict:
    """Load framework configuration from YAML file."""
    config_path = Path(__file__).parent / "frameworks.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
