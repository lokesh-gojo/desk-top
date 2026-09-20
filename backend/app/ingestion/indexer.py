import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.ingestion.chunker import chunk_text
from backend.app.ingestion.crawler import EASACrawler

class DocumentIndexer:
    """
    Ingestion and indexing orchestrator:
    Documents -> Versions (Current vs. Archived) -> Chunks -> Vector DB / Storage.
    Maintains ingestion run audits and crawl errors.
    """
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.audit_log_path = os.path.join(settings.DATA_DIR, "storage", "ingestion_runs.json")
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

    def load_seed_knowledge(self) -> List[Dict[str, Any]]:
        """Load verified bootstrap documents from seed JSON file."""
        if not os.path.exists(settings.SEED_FILE):
            logger.error(f"Seed file not found at {settings.SEED_FILE}")
            return []
        with open(settings.SEED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("documents", [])

    async def run_full_ingestion(self, crawl_live: bool = False) -> Dict[str, Any]:
        """Execute ingestion run with auditing."""
        run_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        
        pages_scanned = 0
        new_docs = 0
        updated_docs = 0
        chunks_generated = 0
        error_count = 0
        
        # 1. Gather documents: Seed files + optional live crawl
        docs_to_index = self.load_seed_knowledge()
        new_docs = len(docs_to_index)
        pages_scanned += len(docs_to_index)
        
        if crawl_live:
            crawler = EASACrawler()
            crawl_res = await crawler.crawl_approved_pages()
            pages_scanned += crawl_res["scanned"]
            error_count += len(crawl_res["errors"])
            for doc in crawl_res["documents"]:
                docs_to_index.append(doc)
                updated_docs += 1

        # 2. Process chunks with metadata
        all_chunks = []
        for doc in docs_to_index:
            metadata = {
                "document_id": doc.get("id", str(uuid.uuid4())),
                "title": doc.get("title", "EASA Document"),
                "category": doc.get("category", "general"),
                "subcategory": doc.get("subcategory", "general"),
                "canonical_url": doc.get("canonical_url", "https://www.easacollege.com"),
                "source_authority": doc.get("source_authority", "official_webpage"),
                "status": doc.get("status", "current"),
                "priority": doc.get("priority", 10),
                "published_date": doc.get("published_date", "2026-01-01"),
                "effective_from": doc.get("effective_from", "2026-01-01"),
                "effective_to": doc.get("effective_to"),
                "last_verified": doc.get("last_verified", "2026-09-20"),
            }
            chunks = chunk_text(doc.get("content", ""), metadata)
            all_chunks.extend(chunks)

        chunks_generated = len(all_chunks)

        # 3. Store in vector store if available
        if self.vector_store:
            self.vector_store.add_chunks(all_chunks)

        completed_at = datetime.now().isoformat()
        audit_record = {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS",
            "pages_scanned": pages_scanned,
            "new_documents": new_docs,
            "updated_documents": updated_docs,
            "archived_documents": 0,
            "chunks_generated": chunks_generated,
            "embeddings_generated": chunks_generated,
            "error_count": error_count,
            "summary_notes": f"Ingested {new_docs} initial verified documents and created {chunks_generated} semantic chunks."
        }

        self._record_audit(audit_record)
        logger.info(f"Ingestion run completed: {audit_record}")
        return audit_record

    def _record_audit(self, record: Dict[str, Any]):
        runs = []
        if os.path.exists(self.audit_log_path):
            try:
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    runs = json.load(f)
            except Exception:
                runs = []
        runs.insert(0, record)
        with open(self.audit_log_path, "w", encoding="utf-8") as f:
            json.dump(runs[:50], f, indent=2)

    def get_latest_audits(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.audit_log_path):
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
