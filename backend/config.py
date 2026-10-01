import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "scout_documents"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LLM_MODEL: str = "gemini-3.8-flash"
    DATA_DIR: str = "backend/data/documents"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_data_path(self) -> Path:
        """Returns the resolved absolute path to the data directory."""
        base_path = Path(__file__).resolve().parent
        data_path = Path(self.DATA_DIR)
        if not data_path.is_absolute():
            # If relative to project root or backend
            if (base_path / data_path).exists():
                return base_path / data_path
            return (base_path.parent / data_path).resolve()
        return data_path


settings = Settings()
