"""Test basic setup and configuration."""

from pathlib import Path

from src.config.settings import Settings, load_framework_config


def test_settings_creation():
    """Test that settings can be created with defaults."""
    # Note: This will fail without .env file, so we test with explicit values
    settings = Settings(
        openai_api_key="test-key",
        pinecone_api_key="test-key",
    )

    assert settings.openai_api_key == "test-key"
    assert settings.pinecone_api_key == "test-key"
    assert settings.pinecone_index_name == "devdocs-index"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.default_chunk_size == 1000
    assert settings.default_overlap == 200


def test_framework_config_loads():
    """Test that framework configuration loads correctly."""
    config = load_framework_config()

    assert "frameworks" in config
    assert "react" in config["frameworks"]
    assert "nextjs" in config["frameworks"]
    assert "typescript" in config["frameworks"]

    # Verify React config structure
    react_config = config["frameworks"]["react"]
    assert react_config["name"] == "React"
    assert react_config["base_url"] == "https://react.dev"
    assert "start_urls" in react_config
    assert "skip_patterns" in react_config
    assert react_config["chunk_size"] == 1000
    assert react_config["overlap"] == 200


def test_data_directory_creation(test_data_dir: Path):
    """Test that test data directory is created."""
    assert test_data_dir.exists()
    assert test_data_dir.is_dir()
