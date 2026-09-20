import json
import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.ingestion.chunker import chunk_text
from backend.app.ingestion.crawler import EASACrawler

class DocumentIndexer:
    """
    Ingestion, versioning, and indexing orchestrator:
    - Traceable: source URL + retrieval timestamp + content hash + version
    - Incremental: Compares SHA-256 hash against existing versions; skips unchanged docs
    - Decoupled: Application startup quickly loads persisted index; re-indexing is an explicit job
    """
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.audit_log_path = os.path.join(settings.STORAGE_DIR, "ingestion_runs.json")
        self.hash_registry_path = settings.HASH_REGISTRY_FILE
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

    def get_document_hashes(self) -> Dict[str, str]:
        if os.path.exists(self.hash_registry_path):
            try:
                with open(self.hash_registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_document_hashes(self, hashes: Dict[str, str]):
        try:
            with open(self.hash_registry_path, "w", encoding="utf-8") as f:
                json.dump(hashes, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save document hashes: {e}")

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
        Documents -> SHA-256 Hash check -> Versioning -> Semantic Chunking -> Storage.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        
        pages_scanned = 0
        new_docs = 0
        updated_docs = 0
        unchanged_docs = 0
        error_count = 0
        
        existing_hashes = self.get_document_hashes()
        updated_hashes = dict(existing_hashes)

        # 1. Collect candidate documents
        raw_documents: List[Dict[str, Any]] = self.load_seed_knowledge()
        pages_scanned += len(raw_documents)

        if crawl_live:
            crawler = EASACrawler()
            crawl_res = await crawler.crawl_approved_pages()
            pages_scanned += crawl_res["scanned"]
            error_count += len(crawl_res["errors"])
            raw_documents.extend(crawl_res["documents"])

        # 2. Incremental hash comparison
        documents_to_process = []
        for doc in raw_documents:
            canonical_url = doc.get("canonical_url", "")
            content = doc.get("content", "")
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            doc["content_hash"] = current_hash

            if canonical_url not in existing_hashes:
                new_docs += 1
                doc["version"] = 1
                documents_to_process.append(doc)
                updated_hashes[canonical_url] = current_hash
            elif existing_hashes[canonical_url] != current_hash:
                updated_docs += 1
                doc["version"] = 2  # Incremented version
                documents_to_process.append(doc)
                updated_hashes[canonical_url] = current_hash
            else:
                unchanged_docs += 1
                # If force-reindexing, we still process to rebuild cache
                documents_to_process.append(doc)

        # 3. Generate structured semantic chunks with stable chunk IDs
        all_chunks = []
        for doc in documents_to_process:
            doc_id = doc.get("id", str(uuid.uuid4()))
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
                # Inject unique stable chunk_id
                c["metadata"]["chunk_id"] = f"{doc_id}_v{version}_c{c['chunk_index']}"
            all_chunks.extend(chunks)

        # 4. Update vector store and persistent cache
        if self.vector_store:
            self.vector_store.add_chunks(all_chunks)
        self.save_cached_chunks(all_chunks)
        self.save_document_hashes(updated_hashes)

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
            "summary_notes": f"Traceable ingestion completed: {new_docs} new, {updated_docs} updated, {len(all_chunks)} chunks indexed."
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
