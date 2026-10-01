from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import settings


class GeminiEmbeddingService:
    """Wrapper for generating text embeddings using Google Generative AI / Gemini API."""
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY).strip()
        raw_model = model_name or settings.EMBEDDING_MODEL
        self.model_name = raw_model if raw_model.startswith("models/") else f"models/{raw_model}"

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please provide it in .env or environment variables."
            )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=self.api_key
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of document chunk texts."""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Generates embedding for a single user query."""
        return self.embeddings.embed_query(text)
