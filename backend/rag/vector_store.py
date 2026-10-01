import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from models.schemas import DocumentChunk
from database.qdrant import get_qdrant_client
from config import settings


class QdrantVectorStore:
    """Manages collection creation, vector upserts, and similarity searches in Qdrant."""

    def __init__(self, client: QdrantClient = None, collection_name: str = None):
        self.client = client or get_qdrant_client()
        self.collection_name = collection_name or settings.QDRANT_COLLECTION

    def ensure_collection(self, vector_size: int = 768):
        """Creates the collection if it does not already exist."""
        collections_response = self.client.get_collections()
        existing_names = [c.name for c in collections_response.collections]

        if self.collection_name not in existing_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )

    def delete_collection(self):
        """Deletes the collection if it exists to reset all stored vectors."""
        collections_response = self.client.get_collections()
        existing_names = [c.name for c in collections_response.collections]
        if self.collection_name in existing_names:
            self.client.delete_collection(collection_name=self.collection_name)

    def upsert_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ):
        """Stores chunks with embeddings and metadata payloads in Qdrant."""
        if not chunks:
            return

        vector_size = len(embeddings[0])
        self.ensure_collection(vector_size=vector_size)

        points = []
        for chunk, emb in zip(chunks, embeddings):
            payload = {
                "content": chunk.content,
                "document_name": chunk.metadata.document_name,
                "document_id": chunk.metadata.document_id,
                "page_number": chunk.metadata.page_number,
                "chunk_id": chunk.metadata.chunk_id,
                "section": chunk.metadata.section,
                "subsection": chunk.metadata.subsection
            }

            # Generate a deterministic or random UUID for point id
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.metadata.chunk_id))

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Executes similarity search on Qdrant and returns the top_k scoring chunk payloads.
        """
        k = top_k or settings.TOP_K
        
        # Check if collection exists
        collections_response = self.client.get_collections()
        existing_names = [c.name for c in collections_response.collections]
        if self.collection_name not in existing_names:
            return []

        # Use query_points (modern qdrant-client) with fallback to search
        if hasattr(self.client, "query_points"):
            search_response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=k
            )
            search_results = search_response.points
        else:
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=k
            )

        results = []
        for res in search_results:
            results.append({
                "content": res.payload.get("content", ""),
                "document_name": res.payload.get("document_name", ""),
                "document_id": res.payload.get("document_id", ""),
                "page_number": res.payload.get("page_number", 0),
                "chunk_id": res.payload.get("chunk_id", ""),
                "score": res.score
            })

        return results
