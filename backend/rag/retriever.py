from typing import List, Dict, Any
from rag.embeddings import GeminiEmbeddingService
from rag.vector_store import QdrantVectorStore
from config import settings


class Retriever:
    """Handles query embedding and retrieval of the top-k relevant chunks."""

    def __init__(
        self,
        embedding_service: GeminiEmbeddingService = None,
        vector_store: QdrantVectorStore = None
    ):
        self.embedding_service = embedding_service or GeminiEmbeddingService()
        self.vector_store = vector_store or QdrantVectorStore()

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Takes user query, generates query embedding, and retrieves top_k chunks.
        """
        k = top_k or settings.TOP_K
        query_vector = self.embedding_service.embed_query(query)
        retrieved_chunks = self.vector_store.similarity_search(query_vector=query_vector, top_k=k)
        return retrieved_chunks
