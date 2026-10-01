import logging
import re
import time
from pathlib import Path
from typing import Optional, List
from models.schemas import (
    IngestResponse,
    QueryResponse,
    SourceItem
)
from rag.extractor import PDFExtractor
from rag.chunker import DocumentChunker
from rag.embeddings import GeminiEmbeddingService
from rag.vector_store import QdrantVectorStore
import uuid
from rag.retriever import Retriever
from rag.bm25_retriever import BM25Retriever
from rag.hybrid_retriever import HybridRetriever
from rag.memory import ConversationMemory
from rag.cloudinary_storage import CloudinaryStorageService
from rag.generator import AnswerGenerator
from config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Coordinates the end-to-end ingestion, hybrid retrieval, memory, and generation pipelines for Scout AI."""

    def __init__(self):
        self.extractor = PDFExtractor()
        self.chunker = DocumentChunker()
        self.embedding_service = GeminiEmbeddingService()
        self.vector_store = QdrantVectorStore()
        self.bm25_retriever = BM25Retriever()
        self.memory = ConversationMemory()
        self.cloudinary = CloudinaryStorageService()
        self.dense_retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store
        )
        self.retriever = self.dense_retriever  # For standalone dense retrieval
        self.hybrid_retriever = HybridRetriever(
            dense_retriever=self.dense_retriever,
            bm25_retriever=self.bm25_retriever,
            rrf_k=60
        )
        self.generator = AnswerGenerator()

    def _embed_batch_with_retry(
        self,
        batch_texts: List[str],
        batch_index: int,
        total_batches: int,
        max_retries: int = 8,
        initial_backoff: float = 5.0
    ) -> List[List[float]]:
        """
        Embeds a single batch of texts with exponential backoff and retry specifically
        for 429 / RESOURCE_EXHAUSTED rate-limit errors.
        """
        for attempt in range(max_retries + 1):
            try:
                return self.embedding_service.embed_documents(batch_texts)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = (
                    "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                    or "Quota exceeded" in err_str
                    or "rate-limit" in err_str.lower()
                )

                if not is_rate_limit:
                    # Do not retry unrelated errors (e.g., 400 Bad Request, 401 Unauthenticated, 404 Not Found)
                    raise e

                if attempt == max_retries:
                    logger.error(
                        f"Failed embedding batch {batch_index}/{total_batches} after {max_retries} retries due to quota exhaustion."
                    )
                    raise RuntimeError(
                        f"Gemini embedding quota/rate limits were exhausted while processing batch {batch_index}/{total_batches}. "
                        f"Please wait before retrying or upgrade your Gemini API quota. Details: {err_str}"
                    ) from e

                # Calculate backoff delay
                delay = initial_backoff * (2 ** attempt)

                # Extract suggested retryDelay from various Gemini error formats:
                # 1. 'retryDelay': '35s'
                # 2. 'Please retry in 35.674218968s.'
                delay_match = re.search(r"(?:retryDelay['\":\s]+|retry in\s+)(\d+(?:\.\d+)?)\s*s?", err_str, re.IGNORECASE)
                if delay_match:
                    try:
                        suggested_delay = float(delay_match.group(1))
                        delay = max(suggested_delay + 2.0, delay)
                    except ValueError:
                        pass

                # Cap maximum single wait at 90s to avoid excessive stall
                delay = min(delay, 90.0)

                logger.warning(
                    f"[Rate Limit 429] Batch {batch_index}/{total_batches} hit quota limit. "
                    f"Retrying attempt {attempt + 1}/{max_retries} in {delay:.1f}s..."
                )
                time.sleep(delay)

        raise RuntimeError("Unexpected failure during batch embedding retry loop.")

    def ingest_document(
        self,
        file_path_str: Optional[str] = None,
        reset_collection: bool = False
    ) -> IngestResponse:
        """
        Executes ingestion for a single file or directory of documents (PDF, TXT, MD).
        """
        if reset_collection:
            self.vector_store.delete_collection()
            self.bm25_retriever.clear()

        if file_path_str:
            target_path = Path(file_path_str)
            if not target_path.is_absolute():
                base_path = Path(__file__).resolve().parent.parent
                if (base_path / target_path).exists():
                    target_path = base_path / target_path
        else:
            target_path = settings.get_data_path()

        if not target_path.exists():
            raise FileNotFoundError(f"Path does not exist: {target_path}")

        files_to_process = []
        if target_path.is_dir():
            for ext in ["*.pdf", "*.txt", "*.md"]:
                files_to_process.extend(target_path.glob(ext))
        else:
            files_to_process = [target_path]

        if not files_to_process:
            raise FileNotFoundError(f"No supported document files (.pdf, .txt, .md) found in: {target_path}")

        all_chunks = []
        for file in files_to_process:
            if file.name.startswith("."):
                continue
            pages_data = self.extractor.extract_pages(file)
            if pages_data:
                chunks = self.chunker.chunk_pages(pages_data)
                all_chunks.extend(chunks)

        if not all_chunks:
            raise ValueError("No extractable content or chunks could be generated from the target files.")

        # Batch embed documents in batches of 50 with rate-limit retries
        batch_size = 50
        all_embeddings = []
        total_batches = (len(all_chunks) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(all_chunks), batch_size), start=1):
            batch = all_chunks[i:i + batch_size]
            batch_texts = [c.content for c in batch]

            # Embed current batch (only retries this batch if it hits 429)
            batch_embeddings = self._embed_batch_with_retry(
                batch_texts=batch_texts,
                batch_index=batch_idx,
                total_batches=total_batches,
                max_retries=5,
                initial_backoff=5.0
            )
            all_embeddings.extend(batch_embeddings)

            # Small delay between successful batches to respect per-minute rate limits
            if batch_idx < total_batches:
                time.sleep(1.5)

        # Store in Qdrant (dense vectors)
        self.vector_store.upsert_chunks(all_chunks, all_embeddings)

        # Build and update BM25 index (sparse keyword search)
        self.bm25_retriever.build_index(all_chunks)

        doc_name = target_path.name
        doc_id = all_chunks[0].metadata.document_id

        return IngestResponse(
            message=f"Successfully ingested {len(files_to_process)} document(s) with {len(all_chunks)} total chunks.",
            document_name=doc_name,
            document_id=doc_id,
            total_chunks=len(all_chunks),
            collection=self.vector_store.collection_name
        )

    def ingest_file_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        reset_collection: bool = False
    ) -> IngestResponse:
        """
        1. Uploads the document to Cloudinary storage.
        2. Extracts pages directly from bytes without writing to disk.
        3. Chunks the text.
        4. Generates Gemini embeddings with 429 rate-limit backoff.
        5. Stores dense vectors in Qdrant and sparse tokens in BM25.
        """
        if reset_collection:
            self.vector_store.delete_collection()
            self.bm25_retriever.clear()

        # 1. Upload to Cloudinary
        upload_meta = self.cloudinary.upload_file(
            file_bytes=file_bytes,
            filename=filename,
            folder="scout_documents"
        )
        logger.info(f"Uploaded to Cloudinary: {upload_meta.get('url')}")

        # 2. Extract
        pages_data = self.extractor.extract_from_bytes(file_bytes=file_bytes, filename=filename)
        if not pages_data:
            raise ValueError(f"No extractable text found in file: {filename}")

        # 3. Chunk
        chunks = self.chunker.chunk_pages(pages_data)
        if not chunks:
            raise ValueError(f"Could not generate chunks from file: {filename}")

        # 4. Embed in batches of 50 with 429 rate-limit retries
        batch_size = 50
        all_embeddings = []
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(chunks), batch_size), start=1):
            batch = chunks[i:i + batch_size]
            batch_texts = [c.content for c in batch]

            batch_embeddings = self._embed_batch_with_retry(
                batch_texts=batch_texts,
                batch_index=batch_idx,
                total_batches=total_batches,
                max_retries=5,
                initial_backoff=5.0
            )
            all_embeddings.extend(batch_embeddings)

            if batch_idx < total_batches:
                time.sleep(1.5)

        # 5. Store in Qdrant & BM25
        self.vector_store.upsert_chunks(chunks, all_embeddings)
        self.bm25_retriever.build_index(chunks)

        doc_id = chunks[0].metadata.document_id

        return IngestResponse(
            message=f"Uploaded to Cloudinary and indexed {len(chunks)} chunks from {filename}.",
            document_name=filename,
            document_id=doc_id,
            total_chunks=len(chunks),
            collection=self.vector_store.collection_name
        )

    # def ingest_pdf(self, file_path_str: Optional[str] = None) -> IngestResponse:
    #     """Alias for ingest_document for backwards compatibility."""
    #     return self.ingest_document(file_path_str=file_path_str)

    def query(self, question: str, conversation_id: Optional[str] = None) -> QueryResponse:
        """
        Executes hybrid query pipeline with conversation memory:
        1. Resolve or create conversation_id.
        2. Load prior conversation history for context.
        3. Dense Vector Search + BM25 Keyword Search with RRF Fusion.
        4. Generate grounded answer via Gemini using context + chat history.
        5. Persist user question and generated answer to memory.
        6. Return QueryResponse including conversation_id.
        """
        # 1. Resolve conversation_id (continue existing or start new)
        conv_id = (conversation_id or "").strip()
        if not conv_id:
            conv_id = str(uuid.uuid4())

        # 2. Retrieve conversation history
        chat_history_str = self.memory.format_history_for_prompt(conv_id, limit=10)

        # 3. Retrieve top chunks using Hybrid Retrieval (Dense + BM25 fused via RRF)
        retrieved_chunks = self.hybrid_retriever.retrieve(
            query=question,
            top_k=settings.TOP_K,
            retrieve_k=10
        )

        # 4. Generate grounded answer with chat history context
        answer = self.generator.generate_answer(
            query=question,
            context_chunks=retrieved_chunks,
            chat_history=chat_history_str
        )

        # 5. Persist messages to isolated conversation memory
        self.memory.add_message(conv_id, role="user", content=question)
        self.memory.add_message(conv_id, role="assistant", content=answer)

        # 6. Format sources
        sources = [
            SourceItem(
                document=chunk.get("document_name", ""),
                page=chunk.get("page_number", 0),
                chunk_id=chunk.get("chunk_id", "")
            )
            for chunk in retrieved_chunks
        ]

        return QueryResponse(
            answer=answer,
            sources=sources,
            conversation_id=conv_id
        )
