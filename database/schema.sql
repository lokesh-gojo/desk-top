-- ==============================================================================
-- EASA DeskBot: Database Schema & pgvector Setup (Production V2)
-- EASA College of Engineering and Technology - AI Helpdesk
-- ==============================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Document Registry (Canonical documents)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_url TEXT NOT NULL UNIQUE,
    document_type TEXT NOT NULL DEFAULT 'webpage', -- 'webpage', 'pdf', 'notice', 'faq', 'policy'
    title TEXT NOT NULL,
    category TEXT NOT NULL,                        -- 'admission', 'course', 'hostel', 'transport', 'facility', etc.
    department TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Document Versions (Temporal tracking: Current vs. Archived)
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    content_hash TEXT NOT NULL,                    -- SHA-256 hash to detect changes
    published_date DATE,
    effective_from DATE,
    effective_to DATE,
    status TEXT NOT NULL DEFAULT 'current',        -- 'current', 'archived', 'superseded'
    source_authority TEXT NOT NULL DEFAULT 'official_webpage', 
    -- Hierarchy: 'official_notice' > 'official_webpage' > 'official_pdf' > 'official_archived' > 'unverified'
    priority INTEGER NOT NULL DEFAULT 10,          -- 10 = current active, 2 = archived
    source_url TEXT NOT NULL,
    verified_at DATE DEFAULT CURRENT_DATE,
    raw_content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_status ON document_versions(status);
CREATE INDEX IF NOT EXISTS idx_doc_versions_effective ON document_versions(effective_from, effective_to);

-- 4. Document Chunks (Vector Store)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    embedding vector(384),                         -- 384 dimensions for BGE-small / MiniLM (or 1024/768 for BGE-M3)
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW vector index for ultra-fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text keyword search index on chunk content
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts 
ON document_chunks 
USING gin (to_tsvector('english', content));

-- 5. Dynamic College Notices (Real-time announcements with automatic expiry)
CREATE TABLE IF NOT EXISTS notices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',     -- 'exam', 'admission', 'event', 'holiday', 'bus'
    content TEXT NOT NULL,
    published_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiry_date DATE,
    status TEXT NOT NULL DEFAULT 'active',        -- 'active', 'expired', 'draft'
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notices_status_expiry ON notices(status, expiry_date);

-- 6. Pre-verified FAQs (Instant exact cache)
CREATE TABLE IF NOT EXISTS faq (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    verified_at DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Feedback Loop (Thumbs Up / Down + User notes)
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating TEXT NOT NULL,                         -- 'helpful', 'unhelpful'
    feedback_text TEXT,
    sources_cited JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Unanswered Questions (Critical intelligence to spot knowledge gaps)
CREATE TABLE IF NOT EXISTS unanswered_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    category_inferred TEXT,
    last_asked_at TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_unanswered_query ON unanswered_questions(query);

-- 9. Ingestion Runs (Crawler & indexing audit log)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',       -- 'running', 'success', 'failed'
    pages_scanned INTEGER DEFAULT 0,
    new_documents INTEGER DEFAULT 0,
    updated_documents INTEGER DEFAULT 0,
    archived_documents INTEGER DEFAULT 0,
    chunks_generated INTEGER DEFAULT 0,
    embeddings_generated INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    summary_notes TEXT
);

-- 10. Crawl Errors (Audit trail for broken links / ingestion issues)
CREATE TABLE IF NOT EXISTS crawl_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status_code INTEGER,
    error_message TEXT,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- Hybrid Search Function (Vector Cosine + Full-Text Search with Temporal Filter)
-- ==============================================================================
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL,
    filter_status TEXT DEFAULT 'current'
)
RETURNS TABLE (
    chunk_id UUID,
    version_id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    status TEXT,
    source_authority TEXT,
    priority INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id AS chunk_id,
        dc.version_id,
        dc.content,
        dc.metadata,
        (1 - (dc.embedding <=> query_embedding))::FLOAT AS similarity,
        dv.status,
        dv.source_authority,
        dv.priority
    FROM document_chunks dc
    JOIN document_versions dv ON dc.version_id = dv.id
    WHERE 
        (filter_status IS NULL OR dv.status = filter_status)
        AND (filter_category IS NULL OR dc.metadata->>'category' = filter_category)
        AND (dv.effective_to IS NULL OR dv.effective_to >= CURRENT_DATE)
    ORDER BY dv.priority DESC, dc.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;
