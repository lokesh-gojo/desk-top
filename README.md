# 🎓 EASA DeskBot – AI College Helpdesk (V2 Production Architecture)

> **Official AI Information Assistant & Digital Reception Desk**  
> **EASA College of Engineering and Technology (Autonomous)**  
> *Palakkad Main Road, Navakkarai, Coimbatore, Tamil Nadu – 641105*  
> *Approved by AICTE, Affiliated to Anna University, Accredited with NAAC 'A' Grade, Autonomous from 2024*  
> *TNEA Single Window Counselling Code: 2755*

---

## 🏛️ System Overview

**EASA DeskBot** is a college-specific, **Strict Source-Grounded RAG Helpdesk** engineered to serve prospective students, parents, current scholars, and visitors with verified institutional knowledge. 

### Core Design Philosophy:
* **No Retrieved Evidence → No Factual Answer → Controlled Fallback**  
  The system strictly refuses to invent or hallucinate admission fees, cutoffs, bus routes, or internal phone numbers.
* **Temporal Awareness**: Automatically distinguishes between active 2026–27 admission notices and historical/archived institutional pages.
* **Evidence & Confidence Gate**: Queries are evaluated against multiple signals (vector similarity, BM25 keyword relevance, reranker score, source authority, and date validity) before triggering LLM generation.
* **Bilingual Interaction**: Native support for **English** and **Tamil (தமிழ்)**.
* **Digital Reception Desk UI**: Modeled as an interactive college reception portal with quick category chips, live circular ribbons, voice input, and an admin operations drawer.

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
                         [ Multilingual Embeddings ]
                                       ↓
                     ┌─────────────────┴─────────────────┐
                     │        HYBRID STORAGE LAYER       │
                     │  Supabase pgvector / Local Index  │
                     └─────────────────┬─────────────────┘
                                       │
     User Query ───→ [ Security Guardrails & Input Sanitizer ]
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ↓                                           ↓
        [ Dense Vector Search ]                     [ BM25 Keyword Search ]
      (Semantic Intent Matching)                   (Exact Codes, ECE, Routes)
                 │                                           │
                 └─────────────────────┬─────────────────────┘
                                       ↓
                       [ Reciprocal Rank Fusion (RRF) ]
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
     "Please contact admission office            (Google GenAI Gemini 2.5 /
       at +91 97888 88888"                       OpenAI / Ollama)
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
│   │   ├── main.py                  # FastAPI entry point & lifespan manager
│   │   ├── api/
│   │   │   ├── chat.py              # POST /api/chat
│   │   │   ├── notices.py           # GET, POST /api/notices
│   │   │   ├── feedback.py          # POST, GET /api/feedback
│   │   │   └── admin.py             # GET /api/admin/unanswered, audits, reindex
│   │   ├── core/
│   │   │   ├── config.py            # Environment settings (Pydantic)
│   │   │   ├── logging.py           # Structured logger
│   │   │   └── security.py          # Prompt injection & ERP privacy filters
│   │   ├── rag/
│   │   │   ├── embeddings.py        # SentenceTransformers / Lightweight fallback
│   │   │   ├── vector_search.py     # Supabase pgvector & local vector search
│   │   │   ├── bm25_search.py       # Inverted index BM25 for exact codes/terms
│   │   │   ├── fusion.py            # Reciprocal Rank Fusion (RRF)
│   │   │   ├── reranker.py          # Cross-feature authority & recency reranker
│   │   │   ├── confidence.py        # Multi-signal evidence confidence gate
│   │   │   └── pipeline.py          # End-to-end RAG pipeline
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
│   │   │   └── indexer.py           # Ingestion manager & audit logger
│   │   ├── models/
│   │   │   └── schema.py            # Request / Response schemas
│   │   └── prompts/
│   │       └── system_prompt.py     # Zero-invention system prompt & Tamil templates
│   ├── data/
│   │   ├── seed/
│   │   │   └── easa_seed_knowledge.json # 10 verified EASA institutional datasets
│   │   └── raw/                     # Traceable raw downloaded HTML pages
│   ├── tests/
│   │   ├── test_retrieval.py        # Courses, ECE, buses, hostels
│   │   ├── test_hallucination.py    # Controlled fallback tests
│   │   ├── test_temporal.py         # 2026-27 vs legacy precedence
│   │   └── test_security.py         # Injection & private records refusal
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                   # Digital College Reception Desk UI
│   ├── app.js                       # Client logic, speech recognition, admin hub
│   ├── style.css                    # Academic navy & amber glassmorphic theme
│   ├── package.json
│   └── Dockerfile
├── database/
│   └── schema.sql                   # Supabase PostgreSQL + pgvector schema
├── run_tests.py                     # Standalone automated verification runner
├── docker-compose.yml               # Multi-container orchestration
├── render.yaml                      # Render cloud deployment specification
├── cloudrun.yaml                    # Google Cloud Run Knative specification
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚡ Quickstart

### 1. Local Python Setup
```bash
# Clone or navigate to the directory
cd "d:/desk bot project"

# Install dependencies
pip install -r backend/requirements.txt

# Run the test verification suite
python run_tests.py

# Start backend server (serves frontend automatically)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to experience the Digital Reception Desk.

---

## 🐳 Docker Deployment

To run the entire system with Docker:
```bash
# Build and run container
docker-compose up --build
```
The application will be live at `http://localhost:8000`.

---

## ☁️ Cloud Deployment (Google Cloud Run / Render)

### Google Cloud Run
1. Build and push container to Google Artifact Registry:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/easa-deskbot:latest .
   ```
2. Deploy using `cloudrun.yaml`:
   ```bash
   gcloud run services replace cloudrun.yaml
   ```

### Render / Railway
* Simply connect your GitHub repository `https://github.com/lokesh-gojo/desk-top` to Render or Railway. The included `render.yaml` or `backend/Dockerfile` will automatically deploy the application.

---

## 🔗 Connecting to GitHub

To push this codebase to your GitHub repository:
```bash
git init
git remote add origin https://github.com/lokesh-gojo/desk-top.git
git branch -M main
git add .
git commit -m "feat: complete EASA DeskBot AI College Helpdesk production architecture"
git push -u origin main
```

---

## 🧪 Evaluation Test Results

All 4 test categories pass out of the box:
* **Retrieval Tests**: Verified recall for UG/PG programmes, ECE department acronyms, Gandhipuram bus routes, and hostel capacities.
* **Grounding Tests**: Verified that unrecorded fees and internal schedules trigger controlled fallback rather than hallucinations.
* **Temporal Tests**: Verified that 2026–27 admission circulars take strict priority over legacy 2018 records.
* **Security Tests**: Verified prompt injection defenses and strict refusal to expose ERP/personal student records.
