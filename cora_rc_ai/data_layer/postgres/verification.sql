-- verification.sql
-- Post-run checks for CORA schema

--\echo '1. Extensions'
SELECT extname
FROM pg_extension
WHERE extname IN ('vector', 'pgcrypto')
ORDER BY extname;

--\echo '2. Core tables'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'documents',
    'document_versions',
    'chunks',
    'embeddings',
    'bookmarks',
    'feedback',
    'audit_logs',
    'regulatory_documents',
    'frameworks',
    'domains',
    'categories',
    'topics',
    'document_topic_mappings',
    'document_chunks',
    'chat_sessions',
    'chat_messages',
    'transaction_screenings',
    'compliance_reports'
  )
ORDER BY table_name;

--\echo '3. regulatory_documents columns'
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'regulatory_documents'
  AND column_name IN (
    'title',
    'doc_type',
    'jurisdiction',
    'source_file',
    'source_hash',
    'status',
    'framework_id',
    'domain_id',
    'category_id',
    'document_name',
    'document_type',
    'file_path',
    'tags',
    'document_version',
    'description',
    'file_size_bytes',
    'processed_at',
    'processing_error',
    'uploaded_by',
    'metadata'
  )
ORDER BY column_name;

--\echo '4. document_topic_mappings foreign keys'
SELECT
    conname,
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'document_topic_mappings'
  AND c.contype = 'f'
ORDER BY conname;

--\echo '5. regulatory_documents foreign keys'
SELECT
    conname,
    pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'regulatory_documents'
  AND c.contype = 'f'
ORDER BY conname;

--\echo '6. Indexes'
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'embeddings',
    'chunks',
    'audit_logs',
    'regulatory_documents',
    'document_chunks',
    'chat_sessions',
    'chat_messages',
    'transaction_screenings'
  )
ORDER BY tablename, indexname;

--\echo '7. Vector columns'
SELECT
    table_name,
    column_name,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND udt_name = 'vector'
ORDER BY table_name, column_name;

--\echo '8. Backfill check for document aliases'
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE document_name IS NOT NULL) AS document_name_populated,
    COUNT(*) FILTER (WHERE document_type IS NOT NULL) AS document_type_populated,
    COUNT(*) FILTER (WHERE file_path IS NOT NULL) AS file_path_populated
FROM regulatory_documents;

--\echo '9. Row counts'
SELECT 'documents' AS table_name, COUNT(*) AS row_count FROM documents
UNION ALL
SELECT 'document_versions', COUNT(*) FROM document_versions
UNION ALL
SELECT 'chunks', COUNT(*) FROM chunks
UNION ALL
SELECT 'embeddings', COUNT(*) FROM embeddings
UNION ALL
SELECT 'regulatory_documents', COUNT(*) FROM regulatory_documents
UNION ALL
SELECT 'frameworks', COUNT(*) FROM frameworks
UNION ALL
SELECT 'domains', COUNT(*) FROM domains
UNION ALL
SELECT 'categories', COUNT(*) FROM categories
UNION ALL
SELECT 'topics', COUNT(*) FROM topics
UNION ALL
SELECT 'document_topic_mappings', COUNT(*) FROM document_topic_mappings
UNION ALL
SELECT 'document_chunks', COUNT(*) FROM document_chunks
UNION ALL
SELECT 'chat_sessions', COUNT(*) FROM chat_sessions
UNION ALL
SELECT 'chat_messages', COUNT(*) FROM chat_messages
UNION ALL
SELECT 'transaction_screenings', COUNT(*) FROM transaction_screenings
UNION ALL
SELECT 'compliance_reports', COUNT(*) FROM compliance_reports
ORDER BY table_name;

--\echo '10. Invalid references in mappings'
SELECT COUNT(*) AS orphaned_document_refs
FROM document_topic_mappings dtm
LEFT JOIN regulatory_documents rd ON rd.id = dtm.document_id
WHERE rd.id IS NULL;

SELECT COUNT(*) AS orphaned_topic_refs
FROM document_topic_mappings dtm
LEFT JOIN topics t ON t.id = dtm.topic_id
WHERE t.id IS NULL;

--\echo '11. chat_sessions / chat_messages compatibility'
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('chat_sessions', 'chat_messages')
ORDER BY table_name, ordinal_position;

--\echo '12. Sample document preview'
SELECT
    id,
    title,
    document_name,
    doc_type,
    document_type,
    jurisdiction,
    file_path,
    tags
FROM regulatory_documents
ORDER BY created_at DESC
LIMIT 10;