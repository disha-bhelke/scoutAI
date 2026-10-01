from qdrant_client import QdrantClient
from config import settings


def get_qdrant_client() -> QdrantClient:
    """Returns an initialized QdrantClient instance supporting both local and Qdrant Cloud with API Key."""
    api_key = settings.QDRANT_API_KEY.strip() if settings.QDRANT_API_KEY else None
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=api_key
    )

