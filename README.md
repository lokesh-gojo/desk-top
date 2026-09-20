# 🎓 EASA DeskBot – AI College Helpdesk (V2.1 Production Architecture)

> **Official AI Information Assistant & Digital Reception Desk**  
> **EASA College of Engineering and Technology (Autonomous)**  
> *Palakkad Main Road, Navakkarai, Coimbatore, Tamil Nadu – 641105*  
> *Approved by AICTE, Affiliated to Anna University, Accredited with NAAC 'A' Grade, Autonomous from 2024*  
> *TNEA Single Window Counselling Code: 2755*

---

## 🏛️ System Overview

**EASA DeskBot** is a college-specific, **Strict Source-Grounded RAG Helpdesk** engineered to serve prospective students, parents, current scholars, and visitors with verified institutional knowledge.

### Core Design Principles:
* **No Retrieved Evidence → No Factual Answer → Controlled Fallback**  
  The system strictly refuses to invent or hallucinate admission fees, cutoffs, bus routes, or internal phone numbers.
* **Temporal Awareness**: Distinguishes between active 2026–27 admission notices and historical/archived institutional records.
* **Evidence & Confidence Gate**: Multi-signal confidence check (`vector similarity + BM25 keyword relevance + reranker score + source authority + date validity`) before triggering LLM generation.
* **True Multilingual Embeddings**: Powered by `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions) supporting **English** and **Tamil (தமிழ்)**, perfectly synchronized with Supabase `vector(384)`.
* **Stable Chunk Identifiers**: RRF fusion utilizes deterministic `chunk_id` (`document_id + version + chunk_index`) to eliminate chunk collisions.
* **Decoupled Startup & Persistent Cache**: Server boots instantaneously from persistent vector cache; re-indexing runs incrementally using SHA-256 content hashes.
* **Single-Container Cloud Delivery**: FastAPI backend directly serves the high-performance Digital Reception Desk UI, eliminating multi-container orchestration overhead in production.

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
                   (Status: Current vs. Archived | Priority 10 vs 2)
                                       ↓
                           [ Logical Semantic Chunker ]
                                       ↓
                 [ Multilingual Embeddings (384-dim EN/TA) ]
                                       ↓
                     ┌─────────────────┴─────────────────┐
                     │        HYBRID STORAGE LAYER       │
                     │  Supabase pgvector / Local Index  │
                     └─────────────────┬─────────────────┘
                                       │
     User Query ───→ [ Multi-Layer Security Guardrails ]
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
      hotline +91 97888 88888)                   OpenAI / Ollama)
                                                          │
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
│   │   │   ├── chat.py              # POST /api/chat
│   │   │   ├── notices.py           # GET, POST /api/notices
│   │   │   ├── feedback.py          # POST, GET /api/feedback
│   │   │   └── admin.py             # GET /api/admin/unanswered, audits, reindex
│   │   ├── core/
│   │   │   ├── config.py            # Environment & 384-dim multilingual settings
│   │   │   ├── logging.py           # Structured logger
│   │   │   └── security.py          # Multi-layer injection & output validators
│   │   ├── rag/
│   │   │   ├── embeddings.py        # 384-dim multilingual vectorizer (EN & TA)
│   │   │   ├── vector_search.py     # Supabase pgvector & local vector search
│   │   │   ├── bm25_search.py       # Inverted index BM25 for exact terms
│   │   │   ├── fusion.py            # Chunk-ID based Reciprocal Rank Fusion
│   │   │   ├── reranker.py          # Cross-feature authority & recency reranker
│   │   │   ├── confidence.py        # Multi-signal evidence confidence gate
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
│   │   │   └── indexer.py           # Traceable incremental indexer & caching
│   │   ├── models/
│   │   │   └── schema.py            # Request / Response schemas
│   │   └── prompts/
│   │       └── system_prompt.py     # Database-driven fallback & Tamil templates
│   ├── data/
│   │   ├── seed/
│   │   │   └── easa_seed_knowledge.json # 10 verified EASA institutional datasets
│   │   ├── storage/                 # Persistent index cache & audit logs
│   │   └── raw/                     # Traceable raw downloaded HTML pages
│   ├── tests/
│   │   ├── test_retrieval.py        # Courses, ECE, buses, hostels
│   │   ├── test_hallucination.py    # Controlled fallback tests
│   │   ├── test_temporal.py         # 2026-27 vs legacy precedence
│   │   ├── test_security.py         # Injection & private records refusal
│   │   └── evaluate_rag.py          # Precision & Abstention benchmark evaluation
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                   # Digital College Reception Desk UI
│   ├── app.js                       # Client logic, voice input, admin hub
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

# Run the benchmark evaluation suite
python backend/tests/evaluate_rag.py

# Start backend server (serves frontend automatically)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to experience the Digital Reception Desk.

---

## 🐳 Docker Deployment

The application is packaged as a high-performance single container where FastAPI directly serves the reception desk:
```bash
# Build and run container
docker-compose up --build
```
Live at `http://localhost:8000`.

---

## ☁️ Cloud Deployment (Google Cloud Run / Render)

### Google Cloud Run
1. Build and push container:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/easa-deskbot:latest .
   ```
2. Deploy using `cloudrun.yaml`:
   ```bash
   gcloud run services replace cloudrun.yaml
   ```

### Render
* Connect `https://github.com/lokesh-gojo/desk-top` to Render. The included `render.yaml` or `backend/Dockerfile` will deploy the service automatically.
