-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Legacy document model
CREATE TABLE IF NOT EXISTS documents (
document_id UUID PRIMARY KEY,
title VARCHAR(500) NOT NULL,
source VARCHAR(100) NOT NULL,
document_type VARCHAR(100) NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_versions (
version_id UUID PRIMARY KEY,
document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
version_number INTEGER NOT NULL,
effective_from DATE NOT NULL,
effective_to DATE,
status VARCHAR(50) DEFAULT 'Active',
supersedes UUID REFERENCES document_versions(version_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS chunks (
chunk_id UUID PRIMARY KEY,
version_id UUID REFERENCES document_versions(version_id) ON DELETE CASCADE,
section_name VARCHAR(500),
clause_name VARCHAR(500),
page_number INTEGER NOT NULL,
chunk_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
embedding_id UUID PRIMARY KEY,
chunk_id UUID REFERENCES chunks(chunk_id) ON DELETE CASCADE,
embedding VECTOR(1024) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hnsw_embedding
ON embeddings
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_fts
ON chunks
USING GIN (to_tsvector('english', chunk_text));

-- App support tables
CREATE TABLE IF NOT EXISTS bookmarks (
bookmark_id UUID PRIMARY KEY,
user_id VARCHAR(100) NOT NULL,
session_id VARCHAR(100) NOT NULL,
transaction_payload JSONB,
assessment JSONB NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
feedback_id UUID PRIMARY KEY,
user_id VARCHAR(100) NOT NULL,
session_id VARCHAR(100) NOT NULL,
response_id VARCHAR(100) NOT NULL,
rating VARCHAR(20) NOT NULL,
comments TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
log_id UUID,
user_id VARCHAR(100),
session_id VARCHAR(100),
entity_type VARCHAR(100),
entity_id VARCHAR(200),
action VARCHAR(200) NOT NULL,
actor VARCHAR(200) DEFAULT 'system',
metadata JSONB DEFAULT '{}',
details JSONB,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at DESC);

-- Regulatory documents
CREATE TABLE IF NOT EXISTS regulatory_documents (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
title VARCHAR(500) NOT NULL,
doc_type VARCHAR(100) DEFAULT 'regulation',
jurisdiction VARCHAR(50) DEFAULT 'GLOBAL',
source_file TEXT,
source_hash VARCHAR(64) UNIQUE,
status VARCHAR(50) DEFAULT 'processing',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Taxonomy
CREATE TABLE IF NOT EXISTS frameworks (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(200) NOT NULL UNIQUE,
description TEXT,
created_by VARCHAR(100) DEFAULT 'system',
version VARCHAR(20) DEFAULT 'v1',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS domains (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
framework_id UUID NOT NULL REFERENCES frameworks(id) ON DELETE CASCADE,
name VARCHAR(200) NOT NULL,
description TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (framework_id, name)
);

CREATE TABLE IF NOT EXISTS categories (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
name VARCHAR(200) NOT NULL,
description TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (domain_id, name)
);

CREATE TABLE IF NOT EXISTS topics (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(200) NOT NULL UNIQUE,
topic_type VARCHAR(50) DEFAULT 'Core',
description TEXT,
is_mandatory BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Regulatory document enrichments
ALTER TABLE regulatory_documents
ADD COLUMN IF NOT EXISTS framework_id UUID REFERENCES frameworks(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS domain_id UUID REFERENCES domains(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS regulatory_body VARCHAR(100) DEFAULT 'RBI',
ADD COLUMN IF NOT EXISTS applicable_entity VARCHAR(200),
ADD COLUMN IF NOT EXISTS document_version VARCHAR(100),
ADD COLUMN IF NOT EXISTS version_year VARCHAR(50),
ADD COLUMN IF NOT EXISTS effective_date DATE,
ADD COLUMN IF NOT EXISTS section_reference TEXT,
ADD COLUMN IF NOT EXISTS risk_level VARCHAR(50),
ADD COLUMN IF NOT EXISTS compliance_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS document_name VARCHAR(500),
ADD COLUMN IF NOT EXISTS document_type VARCHAR(100) DEFAULT 'Master Direction',
ADD COLUMN IF NOT EXISTS file_path TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS processing_error TEXT,
ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(200),
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Topic mappings (fixed FK target)
DROP TABLE IF EXISTS document_topic_mappings;

CREATE TABLE IF NOT EXISTS document_topic_mappings (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
document_id UUID NOT NULL REFERENCES regulatory_documents(id) ON DELETE CASCADE,
topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
UNIQUE (document_id, topic_id)
);

-- Chunk store
CREATE TABLE IF NOT EXISTS document_chunks (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
document_id UUID REFERENCES regulatory_documents(id) ON DELETE CASCADE,
chunk_index INTEGER NOT NULL,
content TEXT NOT NULL,
embedding VECTOR(1024),
metadata JSONB DEFAULT '{}',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON document_chunks USING GIN (to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_doc_framework ON regulatory_documents (framework_id);
CREATE INDEX IF NOT EXISTS idx_doc_domain ON regulatory_documents (domain_id);
CREATE INDEX IF NOT EXISTS idx_doc_category ON regulatory_documents (category_id);
CREATE INDEX IF NOT EXISTS idx_doc_tags ON regulatory_documents USING GIN (tags);

-- Chat persistence
CREATE TABLE IF NOT EXISTS chat_sessions (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
session_id VARCHAR(100) NOT NULL UNIQUE,
user_id VARCHAR(100) NOT NULL,
persona VARCHAR(100),
title VARCHAR(300),
started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
last_message_preview TEXT,
metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS chat_messages (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
role VARCHAR(20) NOT NULL,
content TEXT NOT NULL,
citations JSONB DEFAULT '[]',
message_metadata JSONB DEFAULT '{}',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages (session_id, created_at ASC);

-- Screening and reports
CREATE TABLE IF NOT EXISTS transaction_screenings (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
transaction_id VARCHAR(200) NOT NULL,
risk_rating VARCHAR(50),
confidence FLOAT DEFAULT 0.0,
flagged_violations JSONB DEFAULT '[]',
required_actions JSONB DEFAULT '[]',
applicable_regulations JSONB DEFAULT '[]',
citations JSONB DEFAULT '[]',
reasoning_summary TEXT,
screened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_screen_txn ON transaction_screenings (transaction_id);
CREATE INDEX IF NOT EXISTS idx_screen_risk ON transaction_screenings (risk_rating);
CREATE INDEX IF NOT EXISTS idx_screen_time ON transaction_screenings (screened_at DESC);

CREATE TABLE IF NOT EXISTS compliance_reports (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
report_type VARCHAR(50) DEFAULT 'weekly',
from_date VARCHAR(50),
to_date VARCHAR(50),
jurisdiction VARCHAR(50),
content TEXT,
generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill for existing rows
UPDATE regulatory_documents
SET
document_name = COALESCE(document_name, title),
document_type = COALESCE(document_type, doc_type, 'Master Direction'),
file_path = COALESCE(file_path, source_file)
WHERE
document_name IS NULL
OR document_type IS NULL
OR file_path IS NULL;

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS last_message_preview TEXT;