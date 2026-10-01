import logging
from typing import List, Dict, Any, Optional
from rag.retriever import Retriever as DenseRetriever
from rag.bm25_retriever import BM25Retriever
from config import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retriever combining Dense Vector Search (Gemini + Qdrant) and
    Sparse Keyword Search (BM25) using Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        rrf_k: int = 60
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.rrf_k = rrf_k  # Standard RRF constant (typically 60)

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        retrieve_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval:
        1. Runs Dense vector search to get top retrieve_k chunks.
        2. Runs BM25 keyword search to get top retrieve_k chunks.
        3. Fuses both ranked lists using Reciprocal Rank Fusion (RRF).
        4. Deduplicates chunks and returns top_k highest scoring chunks.
        """
        final_k = top_k or settings.TOP_K

        # 1. Dense retrieval
        dense_results = self.dense_retriever.retrieve(query=query, top_k=retrieve_k)

        # 2. BM25 retrieval
        bm25_results = self.bm25_retriever.retrieve(query=query, top_k=retrieve_k)

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: Score(d) = sum( 1 / (k + rank(d)) )
        fused_scores: Dict[str, float] = {}
        chunk_lookup: Dict[str, Dict[str, Any]] = {}
        source_tracking: Dict[str, Dict[str, Any]] = {}

        # Process Dense results
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item.get("chunk_id") or item.get("content")
            rrf_score = 1.0 / (self.rrf_k + rank)

            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + rrf_score
            chunk_lookup[chunk_id] = item
            source_tracking[chunk_id] = {
                "dense_rank": rank,
                "dense_score": item.get("score", 0.0),
                "bm25_rank": None,
                "bm25_score": None,
                "retrieval_source": "dense"
            }

        # Process BM25 results
        for rank, item in enumerate(bm25_results, start=1):
            chunk_id = item.get("chunk_id") or item.get("content")
            rrf_score = 1.0 / (self.rrf_k + rank)

            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + rrf_score
            if chunk_id not in chunk_lookup:
                chunk_lookup[chunk_id] = item
                source_tracking[chunk_id] = {
                    "dense_rank": None,
                    "dense_score": None,
                    "bm25_rank": rank,
                    "bm25_score": item.get("score", 0.0),
                    "retrieval_source": "bm25"
                }
            else:
                source_tracking[chunk_id]["bm25_rank"] = rank
                source_tracking[chunk_id]["bm25_score"] = item.get("score", 0.0)
                source_tracking[chunk_id]["retrieval_source"] = "both (dense + bm25)"

        # 4. Sort deduplicated chunks by RRF score descending
        sorted_chunk_ids = sorted(
            fused_scores.keys(),
            key=lambda cid: fused_scores[cid],
            reverse=True
        )

        final_chunks = []
        logger.info(f"--- [Hybrid Retrieval for: '{query}'] ---")
        for i, cid in enumerate(sorted_chunk_ids[:final_k], start=1):
            chunk_data = dict(chunk_lookup[cid])
            meta = source_tracking[cid]
            chunk_data["rrf_score"] = fused_scores[cid]
            chunk_data["retrieval_source"] = meta["retrieval_source"]
            chunk_data["dense_rank"] = meta["dense_rank"]
            chunk_data["bm25_rank"] = meta["bm25_rank"]

            logger.info(
                f"Rank #{i} | RRF: {fused_scores[cid]:.5f} | Source: {meta['retrieval_source']} | "
                f"Dense Rank: {meta['dense_rank']} | BM25 Rank: {meta['bm25_rank']} | "
                f"Doc: {chunk_data.get('document_name')} | Page: {chunk_data.get('page_number')} | Chunk ID: {cid}"
            )
            final_chunks.append(chunk_data)

        return final_chunks
