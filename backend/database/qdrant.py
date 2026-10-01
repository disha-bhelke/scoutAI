from qdrant_client import QdrantClient
from config import settings


def get_qdrant_client() -> QdrantClient:
    """Returns an initialized QdrantClient instance."""
    return QdrantClient(url=settings.QDRANT_URL)
