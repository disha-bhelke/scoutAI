from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata associated with each document chunk."""
    document_name: str
    document_id: str
    page_number: int
    chunk_id: str
    # Future-proofing fields for section/subsection routing & multi-document support
    section: Optional[str] = None
    subsection: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class DocumentChunk(BaseModel):
    """Represents a chunk of document text along with its metadata."""
    content: str
    metadata: ChunkMetadata


class IngestRequest(BaseModel):
    """Request schema for document ingestion."""
    file_path: Optional[str] = Field(
        default=None,
        description="Optional custom file or directory path. If omitted, ingests from the default documents directory."
    )
    reset_collection: bool = Field(
        default=False,
        description="Whether to delete existing vectors and collection before ingestion."
    )


class IngestResponse(BaseModel):
    """Response schema for document ingestion."""
    message: str
    document_name: str
    document_id: str
    total_chunks: int
    collection: str


class QueryRequest(BaseModel):
    """Request schema for user query."""
    question: str = Field(..., description="The user question or query")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID to continue an existing chat session. If omitted, a new conversation is started."
    )


class SourceItem(BaseModel):
    """Source item in the query response."""
    document: str
    page: int
    chunk_id: str


class QueryResponse(BaseModel):
    """Response schema matching V1 specification with conversation continuity."""
    answer: str
    sources: List[SourceItem]
    conversation_id: str = Field(..., description="The conversation ID for this chat session")


class LoginRequest(BaseModel):
    """Request schema for Admin authentication."""
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class LoginResponse(BaseModel):
    """Response schema for Admin authentication."""
    token: str
    message: str = "Authentication successful"
    username: str


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str = "v1"
