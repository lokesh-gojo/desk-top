import os
import httpx
from datetime import datetime
from typing import List, Dict, Any
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.ingestion.cleaner import clean_html
from backend.app.ingestion.parser import infer_category, extract_temporal_metadata, compute_content_hash

BASE_URL = "https://www.easacollege.com"

# Explicit URL whitelist based on official verified EASA pages
ALLOWED_PATHS = [
    "/",
    "/aboutus.php",
    "/undergraduate-courses-in-coimbatore",
    "/postgraduate-courses-in-coimbatore",
    "/hostel-facilities-at-easa",
    "/life-at-easa-campus",
    "/placement-training-team",
    "/best-placement-engineering-colleges",
    "/teaching-staff",
    "/exam-cell"
]

# Strict blocklist to never ingest private portals, ERP, login, or admin pages
BLOCKED_PATHS = [
    "/login",
    "/erp",
    "/admin",
    "/student",
    "/portal",
    "/wp-admin"
]

class EASACrawler:
    def __init__(self, raw_dir: str = None):
        self.raw_dir = raw_dir or settings.RAW_DIR
        os.makedirs(self.raw_dir, exist_ok=True)

    def is_url_allowed(self, path: str) -> bool:
        for blocked in BLOCKED_PATHS:
            if blocked in path.lower():
                return False
        return any(path.rstrip("/").endswith(p.rstrip("/")) or path == p for p in ALLOWED_PATHS)

    async def crawl_approved_pages(self) -> Dict[str, Any]:
        """Crawl whitelisted pages, save raw documents, and return extracted records."""
        results = []
        errors = []
        
        headers = {
            "User-Agent": "EASADeskBot-VerifiedCrawler/2.0 (+https://www.easacollege.com)"
        }
        
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            for path in ALLOWED_PATHS:
                url = f"{BASE_URL}{path}" if path != "/" else BASE_URL
                try:
                    logger.info(f"Crawling approved URL: {url}")
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        raw_html = resp.text
                        # Save raw document for traceability
                        filename = path.strip("/").replace(".php", "").replace("/", "_") or "homepage"
                        raw_file_path = os.path.join(self.raw_dir, f"{filename}.html")
                        with open(raw_file_path, "w", encoding="utf-8") as f:
                            f.write(raw_html)
                            
                        cleaned_text = clean_html(raw_html)
                        category = infer_category(url, cleaned_text)
                        temporal_meta = extract_temporal_metadata(cleaned_text)
                        content_hash = compute_content_hash(cleaned_text)
                        
                        title = path.strip("/").replace("-", " ").replace(".php", "").title() or "Homepage & Admission"
                        
                        results.append({
                            "canonical_url": url,
                            "title": f"EASA {title}",
                            "category": category,
                            "content": cleaned_text,
                            "content_hash": content_hash,
                            **temporal_meta
                        })
                    else:
                        errors.append({"url": url, "status_code": resp.status_code, "error": resp.text[:200]})
                except Exception as e:
                    logger.warning(f"Failed to crawl {url}: {e}")
                    errors.append({"url": url, "status_code": 0, "error": str(e)})

        return {
            "scanned": len(ALLOWED_PATHS),
            "succeeded": len(results),
            "errors": errors,
            "documents": results
        }
