import secrets
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File, Form, status
from models.schemas import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    LoginRequest,
    LoginResponse
)
from rag.pipeline import RAGPipeline
from config import settings

router = APIRouter()
rag_pipeline: RAGPipeline = None


def get_pipeline() -> RAGPipeline:
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline


def verify_admin_token(authorization: Optional[str] = Header(None)) -> str:
    """Verifies that the request includes a valid Bearer token for admin actions."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. Admin access required."
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'Bearer <token>'."
        )

    if token != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired admin token."
        )
    return token


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
async def health_check():
    """Health check endpoint to verify backend service status."""
    return HealthResponse(status="healthy", version="v1")


@router.post("/admin/login", response_model=LoginResponse, summary="Admin Authentication")
async def admin_login(creds: LoginRequest):
    """
    Authenticates admin user against configured credentials and returns an access token.
    """
    is_valid_user = secrets.compare_digest(creds.username, settings.ADMIN_USERNAME)
    is_valid_pass = secrets.compare_digest(creds.password, settings.ADMIN_PASSWORD)

    if not (is_valid_user and is_valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    return LoginResponse(
        token=settings.ADMIN_SECRET_KEY,
        message="Admin authentication successful",
        username=creds.username
    )


from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File, Form, status


@router.post("/admin/upload", response_model=IngestResponse, summary="Upload & Ingest to Cloudinary (Admin Protected)")
async def upload_and_ingest_document(
    file: UploadFile = File(...),
    reset_collection: bool = Form(False),
    _: str = Depends(verify_admin_token)
):
    """
    Protected Admin endpoint:
    1. Uploads file to Cloudinary storage (PDF, TXT).
    2. Directly parses the document in memory (no repo/disk storage needed).
    3. Indexes chunks into Qdrant & BM25 with optional reset.
    """
    allowed_extensions = [".pdf", ".txt", ".md"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        file_bytes = await file.read()
        pipeline = get_pipeline()
        response = pipeline.ingest_file_bytes(
            file_bytes=file_bytes,
            filename=file.filename,
            reset_collection=reset_collection
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload & Ingestion failed: {str(e)}"
        )


@router.post("/ingest", response_model=IngestResponse, summary="Ingest Document or Directory (Admin Protected)")
async def ingest_document(
    request: IngestRequest = IngestRequest(),
    _: str = Depends(verify_admin_token)
):
    """
    Protected Admin endpoint: Extracts text from PDF/TXT documents, chunks it with metadata,
    generates embeddings, and stores vectors in Qdrant and BM25.
    """
    try:
        pipeline = get_pipeline()
        response = pipeline.ingest_document(
            file_path_str=request.file_path,
            reset_collection=request.reset_collection
        )
        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse, summary="Query RAG System")
async def query_rag(request: QueryRequest):
    """
    Accepts a user question, retrieves the top 5 relevant document chunks,
    and returns a grounded answer generated by Gemini with source citations.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    try:
        pipeline = get_pipeline()
        response = pipeline.query(
            question=request.question,
            conversation_id=request.conversation_id
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
