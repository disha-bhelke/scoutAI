# Scout AI — Enterprise Hybrid RAG System

Scout AI is an enterprise-grade Retrieval-Augmented Generation (RAG) platform built with **FastAPI**, **Google Gemini API**, **Qdrant Vector Database**, **BM25 Keyword Search**, and **Reciprocal Rank Fusion (RRF)**, featuring persistent SQLite conversation memory and a modern ChatGPT-style dark theme UI.

---

## 🚀 Key Features

- **Hybrid Retrieval (Dense + Sparse)**: Dual retrieval combining Gemini embedding semantic search (`models/gemini-embedding-001`) with BM25 keyword matching (`rank_bm25`).
- **Reciprocal Rank Fusion (RRF)**: Re-ranks and deduplicates retrieved chunks using score fusion without score-scale distortion.
- **Persistent Conversation Memory**: Isolated multi-turn chat memory stored in SQLite (`conversations.db`), enabling contextual follow-up questions per session.
- **Resilient 429 Rate-Limit Handling**: Automatic exponential backoff and `retryDelay` parsing for Gemini free-tier and standard API limits.
- **Qdrant Cloud & Local Support**: Connects seamlessly to both local Docker Qdrant instances and remote managed Qdrant Cloud clusters with API keys.
- **Full-Stack Single Deployment**: FastAPI serves both API routes (`/query`, `/health`, `/ingest`) and the frontend dark-mode chat UI on a single port.

---

## 🏗️ Architecture Pipeline

```text
User Query (POST /query with conversation_id)
  ├── 1. Load Session History (SQLite conversations.db)
  ├── 2. Dense Semantic Search (Gemini embeddings -> Qdrant Cloud/Local)
  └── 3. Sparse Keyword Search (BM25 tokenized index)
        ↓
  4. Reciprocal Rank Fusion (RRF) -> Deduplicate & Top-5 Scoring Chunks
        ↓
  5. Answer Generation (Gemini 3.8 Flash LLM with Context + History)
        ↓
  6. Persist Turn (User Query + Assistant Answer -> SQLite)
        ↓
  7. Return Response (Grounded Answer + Citations + conversation_id)
```

---

## 📁 Project Structure

```text
rag/
├── backend/
│   ├── api/
│   │   └── routes.py           # FastAPI endpoints (/health, /query, /ingest)
│   ├── database/
│   │   └── qdrant.py           # Qdrant client connection (Cloud & Local)
│   ├── models/
│   │   └── schemas.py          # Pydantic schemas (Query, Ingest, Health)
│   ├── rag/
│   │   ├── extractor.py        # PDF and Text document extractor
│   │   ├── chunker.py          # Document chunking & metadata enrichment
│   │   ├── embeddings.py       # Gemini embeddings with auto-prefixing
│   │   ├── vector_store.py     # Qdrant upsert & query_points
│   │   ├── retriever.py        # Standalone Dense Vector retriever
│   │   ├── bm25_retriever.py   # Persistent BM25 keyword retriever
│   │   ├── hybrid_retriever.py # Reciprocal Rank Fusion (RRF) retriever
│   │   ├── memory.py           # Persistent SQLite conversation store
│   │   ├── generator.py        # Grounded LLM answer generator
│   │   └── pipeline.py         # End-to-end RAG orchestrator
│   ├── data/                   # Persistent storage (BM25 index, SQLite db, documents)
│   ├── config.py               # Pydantic Settings & environment manager
│   ├── main.py                 # Application entrypoint & static files mount
│   └── requirements.txt        # Production dependencies
├── frontend/                   # Modern dark-mode Chat UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docker-compose.yml          # Local Qdrant container definition
├── .env.example                # Environment variable configuration reference
├── .gitignore                  # Git ignore rules for virtual environments & secrets
└── README.md
```

---

## 🌐 Deploying on Render

Scout AI can be deployed to **[Render](https://render.com/)** as a **Web Service**.

### Step 1: Push Repository to GitHub / GitLab
Make sure your code is committed and pushed to your remote repository:
```bash
git add .
git commit -m "Prepare production deployment for Render"
git push origin main
```

### Step 2: Create a Web Service on Render
1. Go to the [Render Dashboard](https://dashboard.render.com/) and click **New + > Web Service**.
2. Connect your GitHub/GitLab repository.
3. Configure the service settings:
   - **Name**: `scout-ai-rag`
   - **Region**: Choose the closest region (e.g., Oregon / Frankfurt).
   - **Root Directory**: `backend` (or leave empty if running from root).
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 3: Configure Environment Variables in Render
Under the **Environment** tab in Render, add the following variables:

| Variable Name | Required | Example / Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | `AIzaSy...` (from [Google AI Studio](https://aistudio.google.com/app/apikey)) |
| `QDRANT_URL` | **Yes** | `https://xxxx.us-east-1-0.aws.cloud.qdrant.io:6333` (Your Qdrant Cloud cluster URL) |
| `QDRANT_API_KEY` | **Yes** (Cloud) | `your_qdrant_cloud_api_key` |
| `CLOUDINARY_CLOUD_NAME` | **Yes** (Cloud) | Cloudinary cloud name (stores docs instead of local disk) |
| `CLOUDINARY_API_KEY` | **Yes** (Cloud) | Cloudinary API Key |
| `CLOUDINARY_API_SECRET` | **Yes** (Cloud) | Cloudinary API Secret |
| `ADMIN_USERNAME` | Optional | `admin` (Default) |
| `ADMIN_PASSWORD` | Optional | `admin123` (Default) |
| `ADMIN_SECRET_KEY` | Optional | Random string for Bearer token verification |
| `QDRANT_COLLECTION` | Optional | `scout_documents` (Default) |
| `EMBEDDING_MODEL` | Optional | `models/gemini-embedding-001` (Default) |
| `LLM_MODEL` | Optional | `gemini-3.8-flash` (Default) |
| `CORS_ORIGINS` | Optional | `*` (or your custom domain) |

### Step 4: Add Persistent Disk (Optional but Recommended on Render)
To preserve the SQLite conversation history and BM25 index across dyno reboots:
- In Render service settings, go to **Disks > Add Disk**.
- **Mount Path**: `/opt/render/project/src/backend/data` (or `backend/data`).
- **Size**: `1 GB`.

---

## 💻 Running Locally

### 1. Start Qdrant Container
```bash
docker compose up -d
```

### 2. Set Up Virtual Environment & Dependencies
```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Create `.env` File
Create `backend/.env` (or project root `.env`):
```env
GEMINI_API_KEY=AIzaSyYourActualApiKeyHere
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=scout_documents
EMBEDDING_MODEL=models/gemini-embedding-001
LLM_MODEL=gemini-3.8-flash
```

### 4. Start the Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Open UI: **[http://localhost:8000/](http://localhost:8000/)**
- Swagger API Docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**
- Health Check: **[http://localhost:8000/health](http://localhost:8000/health)**

---

## 📡 API Endpoints

### 1. `GET /health`
Verifies backend service availability (used by Render health checks).

### 2. `POST /query`
Performs hybrid retrieval, pulls conversation memory, and generates an answer.
```json
{
  "question": "What is the policy regarding gifts and benefits?",
  "conversation_id": "optional-uuid-here"
}
```

### 3. `POST /ingest`
Admin endpoint to extract, chunk, embed, and index documents.
```json
{
  "file_path": "data/documents",
  "reset_collection": false
}
```
