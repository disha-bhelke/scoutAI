import uuid
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models.schemas import DocumentChunk, ChunkMetadata
from config import settings


class DocumentChunker:
    """Splits extracted document text into chunks preserving page and document metadata."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk_pages(
        self,
        pages_data: List[Dict[str, Any]],
        document_id: str = None
    ) -> List[DocumentChunk]:
        """
        Takes extracted page items and splits them into chunks with metadata:
        - document_name
        - document_id
        - page_number
        - chunk_id
        """
        if not pages_data:
            return []

        doc_name = pages_data[0].get("document_name", "unknown_document")
        doc_id = document_id or str(uuid.uuid4())

        chunks: List[DocumentChunk] = []
        chunk_sequence = 0

        for page in pages_data:
            page_num = page["page_number"]
            page_text = page["text"]

            split_texts = self.splitter.split_text(page_text)
            for text_chunk in split_texts:
                if not text_chunk.strip():
                    continue

                chunk_sequence += 1
                chunk_id = f"{doc_id}_p{page_num}_c{chunk_sequence}"

                metadata = ChunkMetadata(
                    document_name=doc_name,
                    document_id=doc_id,
                    page_number=page_num,
                    chunk_id=chunk_id,
                    # Placeholders for future section / subsection parsing
                    section=None,
                    subsection=None
                )

                chunks.append(DocumentChunk(
                    content=text_chunk,
                    metadata=metadata
                ))

        return chunks
