import os
import sqlite3
import json
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.schema import NoticeItem, FeedbackRequest, UnansweredQueryItem

class PersistentStorage:
    """
    Unified persistent storage adapter for EASA DeskBot.
    Connects to Supabase PostgreSQL when credentials are configured;
    otherwise persists to an ACID-safe embedded SQLite database (deskbot.db).
    Guarantees notices, feedback, and unanswered queries survive restarts.
    """
    def __init__(self):
        self.db_path = os.path.join(settings.STORAGE_DIR, "deskbot.db")
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        self.supabase_client = None
        self._init_backend()
        self._init_sqlite_schema()

    def _init_backend(self):
        if settings.USE_SUPABASE:
            try:
                from supabase import create_client
                self.supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("PersistentStorage connected to Supabase.")
            except Exception as e:
                logger.warning(f"Failed to connect to Supabase: {e}. Defaulting to persistent SQLite.")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_schema(self):
        """Create tables in SQLite if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Notices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notices (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    published_date TEXT NOT NULL,
                    expiry_date TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    source_url TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            # Feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    feedback_text TEXT,
                    sources_cited TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            # Unanswered queries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unanswered_questions (
                    id TEXT PRIMARY KEY,
                    query TEXT UNIQUE NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    category_inferred TEXT,
                    last_asked_at TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0
                )
            """)
            # Document version registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_versions_registry (
                    canonical_url TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    current_version INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_verified TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

        # Seed initial notices if table is empty
        self._seed_default_notices()

    def _seed_default_notices(self):
        notices = self.get_active_notices()
        if not notices:
            defaults = [
                NoticeItem(
                    id="notice-2026-001",
                    title="B.E / B.Tech Admissions Open 2026-27",
                    category="admission",
                    content="Applications are officially invited for 2026-27 Bachelor of Engineering & Technology admissions. TNEA Single-Window Code: 2755.",
                    published_date="2026-03-01",
                    expiry_date="2026-10-31",
                    status="active",
                    source_url="https://www.easacollege.com/undergraduate-courses-in-coimbatore"
                ),
                NoticeItem(
                    id="notice-2026-002",
                    title="Campus Placement Drive - IT & Core Sectors",
                    category="placement",
                    content="Pre-final and final year students are notified of upcoming pooled campus placement drives scheduled for this semester.",
                    published_date="2026-09-10",
                    expiry_date="2026-11-15",
                    status="active",
                    source_url="https://www.easacollege.com/placement-training-team"
                ),
                NoticeItem(
                    id="notice-2026-003",
                    title="College Bus Routes Schedule - 2026-27",
                    category="transport",
                    content="Updated morning boarding times for Gandhipuram, Singanallur, Pollachi, and Kerala routes are active.",
                    published_date="2026-08-20",
                    expiry_date="2027-05-31",
                    status="active",
                    source_url="https://www.easacollege.com/life-at-easa-campus"
                )
            ]
            for n in defaults:
                self.add_notice(n)

    # ------------------ Notices ------------------
    def get_active_notices(self) -> List[NoticeItem]:
        today = date.today().isoformat()
        if self.supabase_client:
            try:
                res = self.supabase_client.table("notices").select("*").eq("status", "active").gte("expiry_date", today).execute()
                if res.data:
                    return [NoticeItem(**row) for row in res.data]
            except Exception as e:
                logger.warning(f"Supabase notices query failed: {e}. Falling back to SQLite.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notices 
                WHERE status = 'active' AND (expiry_date IS NULL OR expiry_date >= ?)
                ORDER BY published_date DESC
            """, (today,))
            rows = cursor.fetchall()
            return [
                NoticeItem(
                    id=r["id"],
                    title=r["title"],
                    category=r["category"],
                    content=r["content"],
                    published_date=r["published_date"],
                    expiry_date=r["expiry_date"],
                    status=r["status"],
                    source_url=r["source_url"]
                ) for r in rows
            ]

    def add_notice(self, notice: NoticeItem) -> NoticeItem:
        if self.supabase_client:
            try:
                self.supabase_client.table("notices").insert(notice.model_dump()).execute()
                return notice
            except Exception as e:
                logger.warning(f"Supabase notice insert failed: {e}. Falling back to SQLite.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO notices 
                (id, title, category, content, published_date, expiry_date, status, source_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notice.id, notice.title, notice.category, notice.content,
                notice.published_date, notice.expiry_date, notice.status, notice.source_url,
                datetime.now().isoformat()
            ))
            conn.commit()
        return notice

    # ------------------ Feedback ------------------
    def save_feedback(self, fb: FeedbackRequest) -> str:
        fb_id = str(uuid.uuid4())
        sources_json = json.dumps(fb.sources_cited or [])
        now_str = datetime.now().isoformat()

        if self.supabase_client:
            try:
                self.supabase_client.table("feedback").insert({
                    "id": fb_id,
                    "session_id": fb.session_id,
                    "question": fb.question,
                    "answer": fb.answer,
                    "rating": fb.rating,
                    "feedback_text": fb.feedback_text,
                    "sources_cited": fb.sources_cited,
                    "created_at": now_str
                }).execute()
                return fb_id
            except Exception as e:
                logger.warning(f"Supabase feedback insert failed: {e}. Falling back to SQLite.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (id, session_id, question, answer, rating, feedback_text, sources_cited, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fb_id, fb.session_id, fb.question, fb.answer, fb.rating, fb.feedback_text, sources_json, now_str))
            conn.commit()
        return fb_id

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # ------------------ Unanswered Questions ------------------
    def log_unanswered_query(self, query: str, category: str = "general"):
        clean_q = query.strip()
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO unanswered_questions (id, query, frequency, category_inferred, last_asked_at, resolved)
                VALUES (?, ?, 1, ?, ?, 0)
                ON CONFLICT(query) DO UPDATE SET 
                    frequency = frequency + 1,
                    last_asked_at = excluded.last_asked_at
            """, (str(uuid.uuid4()), clean_q, category, now_str))
            conn.commit()

    def get_unanswered_queries(self) -> List[UnansweredQueryItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM unanswered_questions ORDER BY frequency DESC, last_asked_at DESC LIMIT 50")
            rows = cursor.fetchall()
            return [
                UnansweredQueryItem(
                    query=r["query"],
                    frequency=r["frequency"],
                    last_asked_at=r["last_asked_at"],
                    resolved=bool(r["resolved"])
                ) for r in rows
            ]

    # ------------------ Document Version Registry ------------------
    def get_version_record(self, canonical_url: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_versions_registry WHERE canonical_url = ?", (canonical_url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_version_record(self, canonical_url: str, doc_id: str, version: int, content_hash: str, status: str = "current"):
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO document_versions_registry 
                (canonical_url, document_id, current_version, content_hash, last_verified, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_url) DO UPDATE SET 
                    current_version = excluded.current_version,
                    content_hash = excluded.content_hash,
                    last_verified = excluded.last_verified,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            """, (canonical_url, doc_id, version, content_hash, date.today().isoformat(), status, now_str))
            conn.commit()

storage = PersistentStorage()
