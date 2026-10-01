import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "scout_documents"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LLM_MODEL: str = "gemini-3.8-flash"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_SECRET_KEY: str = "scout-ai-secure-admin-token-2026"
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_URL: str = ""
    DATA_DIR: str = "data/documents"
    STORAGE_DIR: str = "data"
    CORS_ORIGINS: str = "*"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent / ".env"),
            str(Path(__file__).resolve().parent.parent / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_storage_path(self) -> Path:
        """Returns the resolved absolute path to the data/storage directory."""
        base_path = Path(__file__).resolve().parent
        storage_path = Path(self.STORAGE_DIR)
        if not storage_path.is_absolute():
            return base_path / storage_path
        return storage_path

    def get_data_path(self) -> Path:
        """Returns the resolved absolute path to the data documents directory."""
        base_path = Path(__file__).resolve().parent
        data_path = Path(self.DATA_DIR)
        if not data_path.is_absolute():
            if (base_path / data_path).exists():
                return base_path / data_path
            return (base_path.parent / data_path).resolve()
        return data_path


settings = Settings()
