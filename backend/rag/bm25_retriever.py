import os
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from models.schemas import DocumentChunk
from config import settings


def tokenize(text: str) -> List[str]:
    """
    Standard lowercase alphanumeric tokenizer for BM25.
    Removes punctuation and splits on whitespace.
    """
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    """
    Lightweight in-memory and disk-persisted BM25 keyword retriever using rank_bm25.
    Indexes DocumentChunk objects and searches using Okapi BM25 scoring.
    """

    def __init__(self, index_path: Optional[str] = None):
        if index_path:
            self.index_path = Path(index_path)
        else:
            storage_dir = settings.get_storage_path()
            storage_dir.mkdir(parents=True, exist_ok=True)
            self.index_path = storage_dir / "bm25_index.pkl"

        self.corpus_chunks: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None

        # Load existing index if available
        self.load()

    def build_index(self, chunks: List[DocumentChunk]):
        """
        Builds and persists the BM25 index over a list of document chunks.
        """
        if not chunks:
            self.corpus_chunks = []
            self.bm25 = None
            self.clear()
            return

        self.corpus_chunks = [
            {
                "content": chunk.content,
                "document_name": chunk.metadata.document_name,
                "document_id": chunk.metadata.document_id,
                "page_number": chunk.metadata.page_number,
                "chunk_id": chunk.metadata.chunk_id,
            }
            for chunk in chunks
        ]

        tokenized_corpus = [tokenize(item["content"]) for item in self.corpus_chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.save()

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Runs BM25 keyword retrieval for the user query and returns the top_k matching chunks.
        """
        k = top_k or settings.TOP_K
        if not self.bm25 or not self.corpus_chunks:
            return []

        tokenized_query = tokenize(query)
        if not tokenized_query:
            return []

        doc_scores = self.bm25.get_scores(tokenized_query)
        # Pair with original indices and sort descending by BM25 score
        scored_indices = sorted(
            enumerate(doc_scores),
            key=lambda x: x[1],
            reverse=True
        )

        results = []
        for idx, score in scored_indices[:k]:
            item = dict(self.corpus_chunks[idx])
            item["score"] = float(score)
            results.append(item)

        return results

    def save(self):
        """Persists the BM25 index and chunk metadata to disk."""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_path, "wb") as f:
                pickle.dump({"corpus_chunks": self.corpus_chunks, "bm25": self.bm25}, f)
        except Exception as e:
            print(f"[Warning] Failed to persist BM25 index to {self.index_path}: {e}")

    def load(self):
        """Loads the BM25 index and chunk metadata from disk if available."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                    self.corpus_chunks = data.get("corpus_chunks", [])
                    self.bm25 = data.get("bm25", None)
            except Exception as e:
                print(f"[Warning] Failed to load BM25 index from {self.index_path}: {e}")

    def clear(self):
        """Removes existing index and deletes persisted file."""
        self.corpus_chunks = []
        self.bm25 = None
        if self.index_path.exists():
            try:
                self.index_path.unlink()
            except Exception:
                pass
