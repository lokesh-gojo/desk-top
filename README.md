# 🎓 EASA DeskBot – AI College Helpdesk (V2.2 Production Architecture)

> **Official AI Information Assistant & Digital Reception Desk**  
> **EASA College of Engineering and Technology (Autonomous)**  
> *Palakkad Main Road, Navakkarai, Coimbatore, Tamil Nadu – 641105*  
> *Approved by AICTE, Affiliated to Anna University, Accredited with NAAC 'A' Grade, Autonomous from 2024*  
> *TNEA Single Window Counselling Code: 2755*

---

## 🏛️ System Overview

**EASA DeskBot** is an enterprise-grade, **Strict Source-Grounded RAG Helpdesk** engineered to serve prospective students, parents, current scholars, and visitors with verified institutional knowledge.

### Core Design Principles:
* **No Retrieved Evidence → No Factual Answer → Controlled Fallback**  
  The system strictly enforces **abstention on unsupported facts**, refusing to invent admission fees, cutoffs, bus routes, or internal phone numbers.
* **Conversational Multi-Turn Context**: An integrated Contextual Query Rewriter resolves conversational pronouns and follow-up questions (*"What about ECE?"*, *"Does it have a boys hostel?"*) into self-contained search queries before retrieval.
* **ACID Persistent Operations**: Notices, user feedback, and unanswered queries are permanently persisted via SQLite/Supabase, guaranteeing zero data loss across container restarts.
* **Admin RBAC Authentication**: All administrative and notice-publishing endpoints are secured with `X-Admin-API-Key` / Bearer token authentication.
* **True Sequential Document Versioning**: Maintains incremental version history (`v1 → v2 → v3`) per canonical URL via SHA-256 content hashing.
* **Native Multilingual Embeddings**: Powered by `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions) supporting **English**, **Tamil (தமிழ்)**, and **Tanglish**, perfectly synchronized with Supabase `vector(384)`.
* **Stable Chunk Identifiers**: RRF fusion utilizes deterministic `chunk_id` (`document_id + version + chunk_index`) to eliminate chunk collisions.
* **Single-Container Cloud Delivery**: FastAPI backend directly serves the high-performance Digital Reception Desk UI with sub-second cold starts from persistent vector caches.

---

## 🏗️ Architecture

```
                               EASA OFFICIAL DATA
                    ┌──────────────────┴──────────────────┐
                    │                                     │
           Live Whitelist Webpages                    Official PDFs
          (easacollege.com/aboutus.php)             & Dynamic Notices
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ↓
                             [ EASACrawler & Ingester ]
                                       ↓
                        [ HTML Cleaner & Metadata Parser ]
                      (SHA-256 Incremental Versioning: v1→v2→v3)
                                       ↓
                           [ Logical Semantic Chunker ]
                                       ↓
                 [ Multilingual Embeddings (384-dim EN/TA) ]
                                       ↓
                     ┌─────────────────┴─────────────────┐
                     │     PERSISTENT STORAGE LAYER      │
                     │  Supabase pgvector / SQLite Cache │
                     │  (Notices, Feedback, Unanswered)  │
                     └─────────────────┬─────────────────┘
                                       │
     User Query ───→ [ Security Guardrails & Delimiter Filter ]
                                       │
                    [ Conversational Query Rewriter ]
                    (Resolves multi-turn chat history)
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ↓                                           ↓
        [ Dense Vector Search ]                     [ BM25 Keyword Search ]
      (Semantic Intent Matching)                   (Exact Codes, ECE, Routes)
                 │                                           │
                 └─────────────────────┬─────────────────────┘
                                       ↓
                   [ Stable Chunk ID RRF Fusion ]
                                       ↓
                  [ Institutional Feature Reranker ]
                 (Authority Boost + Temporal Recency Bonus)
                                       ↓
                  [ Multi-Signal Evidence Confidence Gate ]
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
             [ Weak Evidence ]                     [ Strong Evidence ]
                    │                                     │
                    ↓                                     ↓
         [ Controlled Fallback ]                 [ Pluggable LLM Layer ]
     (Dynamic contacts from DB:                 (Google GenAI Gemini 2.5 /
      hotline +91 97888 88888;                   OpenAI / Ollama)
      logged to unanswered DB)                            │
                                                          ↓
                                                [ Output Validator ]
                                              (Zero prompt/data leak)
                                                          │
                                                          ↓
                                                [ Grounded Response ]
                                             (Answer + Official Citations
                                              + Last Verified: 20 Sep 2026)
```

---

## 📂 Project Structure

```
desk-bot-project/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point & fast-boot loader
│   │   ├── api/
│   │   │   ├── chat.py              # POST /api/chat (Multi-turn conversational RAG)
│   │   │   ├── notices.py           # GET, POST /api/notices (Persistent & RBAC protected)
│   │   │   ├── feedback.py          # POST, GET /api/feedback (Persistent & RBAC protected)
│   │   │   └── admin.py             # GET /api/admin/unanswered, audits, reindex (RBAC protected)
│   │   ├── core/
│   │   │   ├── config.py            # Environment, CORS & Admin API key settings
│   │   │   ├── logging.py           # Structured logger
│   │   │   └── security.py          # Multi-layer injection, output & RBAC validators
│   │   ├── db/
│   │   │   └── storage.py           # Unified persistent database adapter (SQLite + Supabase)
│   │   ├── rag/
│   │   │   ├── embeddings.py        # 384-dim multilingual vectorizer (EN & TA)
│   │   │   ├── vector_search.py     # Supabase pgvector & local vector search
│   │   │   ├── bm25_search.py       # Inverted index BM25 for exact terms
│   │   │   ├── fusion.py            # Chunk-ID based Reciprocal Rank Fusion
│   │   │   ├── reranker.py          # Cross-feature authority & recency reranker
│   │   │   ├── confidence.py        # Multi-signal evidence confidence gate
│   │   │   ├── rewriter.py          # Contextual conversational query rewriter
│   │   │   └── pipeline.py          # Strict Grounded RAG orchestrator
│   │   ├── llm/
│   │   │   ├── base.py              # Abstract LLMProvider interface
│   │   │   ├── gemini.py            # Google GenAI SDK (gemini-2.5-flash)
│   │   │   ├── openai.py            # OpenAI API provider
│   │   │   └── ollama.py            # Local Ollama provider
│   │   ├── ingestion/
│   │   │   ├── crawler.py           # Whitelisted crawler (blocks ERP/admin)
│   │   │   ├── parser.py            # Temporal extractor & SHA-256 versioning
│   │   │   ├── cleaner.py           # HTML sanitizer & boilerplate stripper
│   │   │   ├── chunker.py           # Structured semantic chunker
│   │   │   └── indexer.py           # True sequential versioning (v1→v2→v3)
│   │   ├── models/
│   │   │   └── schema.py            # Request / Response schemas
│   │   └── prompts/
│   │       └── system_prompt.py     # Database-driven fallback & Tamil templates
│   ├── data/
│   │   ├── seed/
│   │   │   └── easa_seed_knowledge.json # 10 verified EASA institutional datasets
│   │   ├── storage/                 # Persistent SQLite database & index cache
│   │   └── raw/                     # Traceable raw downloaded HTML pages
│   ├── tests/
│   │   ├── test_retrieval.py        # Courses, ECE, buses, hostels
│   │   ├── test_hallucination.py    # Controlled fallback tests
│   │   ├── test_temporal.py         # 2026-27 vs legacy precedence
│   │   ├── test_security.py         # Injection & private records refusal
│   │   └── evaluate_rag.py          # Factual accuracy & multilingual benchmark
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                   # Digital College Reception Desk UI
│   ├── app.js                       # Client logic, voice input, admin auth
│   ├── style.css                    # Academic navy & amber glassmorphic theme
│   └── package.json
├── database/
│   └── schema.sql                   # Supabase PostgreSQL + pgvector schema
├── run_tests.py                     # Automated unit test suite runner
├── docker-compose.yml               # Production container orchestration
├── render.yaml                      # Render cloud deployment specification
├── cloudrun.yaml                    # Google Cloud Run Knative specification
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚡ Quickstart & Testing

### 1. Local Python Setup
```bash
# Clone or navigate to workspace
cd "d:/desk bot project"

# Install dependencies
pip install -r backend/requirements.txt

# Run the unit test suite
python run_tests.py

# Run the multilingual benchmark evaluation suite (Factual accuracy & abstention)
python backend/tests/evaluate_rag.py

# Start backend server (serves frontend automatically)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to experience the Digital Reception Desk.

---

## 🔐 Administrative Operations & Security

All administrative routes are protected by **RBAC**:
* **Admin Key**: Set via `ADMIN_API_KEY` in `.env` (default: `easa-admin-key-2026`).
* **Headers**: Provide `X-Admin-API-Key: <YOUR_KEY>` or `Authorization: Bearer <YOUR_KEY>`.
* **Endpoints Protected**:
  * `POST /api/notices` – Publish persistent live announcements.
  * `POST /api/admin/reindex` – Trigger incremental SHA-256 re-indexing.
  * `GET /api/admin/audits` – Inspect crawler and indexing logs.
  * `GET /api/admin/unanswered` – Review questions flagged for knowledge base enrichment.
  * `GET /api/feedback` – Review user ratings.

---

## 🐳 Docker Deployment

The application runs as a high-performance single container:
```bash
docker-compose up --build
```
Live at `http://localhost:8000`.

---

## ☁️ Cloud Deployment (Google Cloud Run / Render)

### Google Cloud Run
1. Build and submit container image:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/easa-deskbot:latest .
   ```
2. Deploy using `cloudrun.yaml`:
   ```bash
   gcloud run services replace cloudrun.yaml
   ```

### Render
* Connect your GitHub repository to Render. The included `render.yaml` automatically deploys the service with persistent storage and environment variables.
