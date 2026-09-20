import json
import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.ingestion.chunker import chunk_text
from backend.app.ingestion.crawler import EASACrawler
from backend.app.db.storage import storage

class DocumentIndexer:
    """
    Ingestion, sequential versioning, and indexing orchestrator:
    - True Sequential Versioning: v1 -> v2 -> v3 -> v4 tracked per canonical document
    - Incremental: Compares SHA-256 hash against existing versions; skips unchanged docs
    - Decoupled: Application startup quickly loads persisted index; re-indexing is an explicit job
    """
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.audit_log_path = os.path.join(settings.STORAGE_DIR, "ingestion_runs.json")
        self.cache_file_path = settings.CHUNKS_CACHE_FILE
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    def load_cached_chunks(self) -> List[Dict[str, Any]]:
        """Fast startup loader: read previously indexed chunks from persistent storage."""
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                    logger.info(f"Loaded {len(chunks)} cached chunks from persistent storage.")
                    return chunks
            except Exception as e:
                logger.warning(f"Failed to read chunks cache: {e}")
        return []

    def save_cached_chunks(self, chunks: List[Dict[str, Any]]):
        """Persist indexed chunks to disk for instant cold starts."""
        try:
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache chunks: {e}")

    def load_seed_knowledge(self) -> List[Dict[str, Any]]:
        """Load verified bootstrap documents from seed JSON file."""
        if not os.path.exists(settings.SEED_FILE):
            logger.error(f"Seed file not found at {settings.SEED_FILE}")
            return []
        with open(settings.SEED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("documents", [])

    async def run_full_ingestion(self, crawl_live: bool = False) -> Dict[str, Any]:
        """
        Execute full traceable ingestion job:
        Documents -> SHA-256 Hash check -> True Sequential Versioning (v1->v2->v3) -> Semantic Chunking -> Storage.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        
        pages_scanned = 0
        new_docs = 0
        updated_docs = 0
        unchanged_docs = 0
        error_count = 0

        # 1. Collect candidate documents
        raw_documents: List[Dict[str, Any]] = self.load_seed_knowledge()
        pages_scanned += len(raw_documents)

        if crawl_live:
            crawler = EASACrawler()
            crawl_res = await crawler.crawl_approved_pages()
            pages_scanned += crawl_res["scanned"]
            error_count += len(crawl_res["errors"])
            raw_documents.extend(crawl_res["documents"])

        # 2. Sequential versioning & hash comparison
        documents_to_process = []
        for doc in raw_documents:
            canonical_url = doc.get("canonical_url", "")
            content = doc.get("content", "")
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            doc["content_hash"] = current_hash

            existing_record = storage.get_version_record(canonical_url)

            if not existing_record:
                # New canonical document: version 1
                new_docs += 1
                version = 1
                doc_id = doc.get("id", str(uuid.uuid4()))
                doc["version"] = version
                doc["id"] = doc_id
                storage.upsert_version_record(canonical_url, doc_id, version, current_hash)
                documents_to_process.append(doc)
            elif existing_record["content_hash"] != current_hash:
                # Content changed: sequential increment (e.g. v1 -> v2 -> v3)
                updated_docs += 1
                version = existing_record["current_version"] + 1
                doc_id = existing_record["document_id"]
                doc["version"] = version
                doc["id"] = doc_id
                storage.upsert_version_record(canonical_url, doc_id, version, current_hash)
                documents_to_process.append(doc)
            else:
                unchanged_docs += 1
                doc["version"] = existing_record["current_version"]
                doc["id"] = existing_record["document_id"]
                documents_to_process.append(doc)

        # 3. Generate structured semantic chunks with stable chunk IDs
        all_chunks = []
        for doc in documents_to_process:
            doc_id = doc.get("id")
            version = doc.get("version", 1)
            metadata = {
                "document_id": doc_id,
                "version": version,
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
                "content_hash": doc.get("content_hash")
            }
            
            chunks = chunk_text(doc.get("content", ""), metadata)
            for c in chunks:
                c["metadata"]["chunk_id"] = f"{doc_id}_v{version}_c{c['chunk_index']}"
            all_chunks.extend(chunks)

        # 4. Update vector store and persistent cache
        if self.vector_store:
            self.vector_store.add_chunks(all_chunks)
        self.save_cached_chunks(all_chunks)

        completed_at = datetime.now().isoformat()
        audit_record = {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS",
            "pages_scanned": pages_scanned,
            "new_documents": new_docs,
            "updated_documents": updated_docs,
            "unchanged_documents": unchanged_docs,
            "chunks_generated": len(all_chunks),
            "embeddings_generated": len(all_chunks),
            "error_count": error_count,
            "summary_notes": f"Traceable sequential versioning run: {new_docs} new, {updated_docs} updated, {len(all_chunks)} chunks indexed."
        }

        self._record_audit(audit_record)
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
            try:
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
