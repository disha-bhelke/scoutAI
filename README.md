# Scout AI - Backend RAG Engine (V1)

Scout AI V1 is a modular, backend-only Retrieval-Augmented Generation (RAG) system built with **FastAPI**, **LangChain**, **PyMuPDF**, **Google Gemini API**, and **Qdrant**.

---

## Architecture Overview

```text
PDF (backend/data/documents/)
 ↓
Text extraction (PyMuPDF - rag/extractor.py)
 ↓
Chunking with metadata (RecursiveCharacterTextSplitter - rag/chunker.py)
 ↓
Embedding generation (Gemini text-embedding-004 - rag/embeddings.py)
 ↓
Store vectors + metadata (Qdrant Vector DB - rag/vector_store.py)
 ↓
User query (POST /query)
 ↓
Query embedding (Gemini)
 ↓
Similarity search (Cosine distance in Qdrant)
 ↓
Retrieve Top 5 chunks (rag/retriever.py)
 ↓
Send retrieved context + query to Gemini (rag/generator.py)
 ↓
Generate grounded answer with document citations
```

---

## Project Structure

```text
rag/
├── backend/
│   ├── api/
│   │   └── routes.py           # FastAPI endpoints (/health, /ingest, /query)
│   ├── database/
│   │   └── qdrant.py           # Qdrant client connection
│   ├── models/
│   │   └── schemas.py          # Pydantic request & response models
│   ├── rag/
│   │   ├── extractor.py        # PyMuPDF PDF extraction
│   │   ├── chunker.py          # Document chunking & metadata enrichment
│   │   ├── embeddings.py       # Google Gemini embedding service
│   │   ├── vector_store.py     # Qdrant upsert & similarity search
│   │   ├── retriever.py        # Top-K chunk retrieval
│   │   ├── generator.py        # Gemini grounded LLM generation
│   │   └── pipeline.py         # Ingestion and query orchestration
│   ├── config.py               # Settings and environment variable loader
│   ├── main.py                 # FastAPI application entrypoint
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── data/
│       └── documents/          # Directory for storing input PDF files
├── docker-compose.yml          # Local Qdrant container definition
└── README.md
```

---

## Getting Started

### 1. Prerequisites

- Python 3.12+
- Docker (for running Qdrant)
- Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### 2. Set Up Environment

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` and set your `GEMINI_API_KEY`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION=scout_documents
   EMBEDDING_MODEL=models/text-embedding-004
   LLM_MODEL=gemini-1.5-flash
   ```

### 3. Start Qdrant Vector Store

Start Qdrant using Docker Compose from the root directory:

```bash
docker-compose up -d
```

Verify Qdrant is running at [http://localhost:6333/dashboard](http://localhost:6333/dashboard).

### 4. Run the FastAPI Server

From the `backend` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation will be available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## API Usage

### 1. Health Check
```bash
curl -X GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "v1"
}
```

### 2. Ingest PDF Document

Place your PDF in `backend/data/documents/` (e.g., `backend/data/documents/sample.pdf`), then call:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{}'
```

*Or specify a custom file path:*
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "backend/data/documents/sample.pdf"}'
```

**Response:**
```json
{
  "message": "Successfully ingested and indexed document: sample.pdf",
  "document_name": "sample.pdf",
  "document_id": "9f257a05-1a2c-4903-8877-cbf046538f72",
  "total_chunks": 18,
  "collection": "scout_documents"
}
```

### 3. Query the RAG System

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings discussed in the document?"}'
```

**Response:**
```json
{
  "answer": "The document highlights three primary findings...",
  "sources": [
    {
      "document": "sample.pdf",
      "page": 2,
      "chunk_id": "9f257a05-1a2c-4903-8877-cbf046538f72_p2_c3"
    },
    {
      "document": "sample.pdf",
      "page": 5,
      "chunk_id": "9f257a05-1a2c-4903-8877-cbf046538f72_p5_c7"
    }
  ]
}
```

---

## Future Roadmap (V2+)

The modular structure allows extending features without rewriting core components:
- **Query Routing & Agents**: LangGraph integration
- **Hybrid Retrieval**: BM25 + dense vector fusion
- **Reranking**: Cross-encoder rerankers
- **Metadata Routing**: Section/subsection extraction
- **Database**: PostgreSQL / Prisma for chat history and document tracking
- **Evaluation**: Ragas / TruLens benchmark suite
