import os
import uuid
import logging
from typing import List, Dict, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

logger = logging.getLogger(__name__)

class PgVectorAdapter:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", 5432))
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        self.dbname = os.getenv("DB_NAME", "cora_db")
        self._conn = None

    def get_connection(self):
        if self._conn is None or self._conn.closed != 0:
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.dbname
            )
            # Ensure pgvector extension is enabled
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self._conn.commit()
        return self._conn

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description is not None:
                return cur.fetchall()
            conn.commit()
            return []

    def save_document(self, doc_id: str, title: str, source: str, doc_type: str) -> None:
        query = """
            INSERT INTO documents (document_id, title, source, document_type, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (document_id) DO UPDATE SET title = EXCLUDED.title;
        """
        self.execute_query(query, (doc_id, title, source, doc_type))

    def save_version(self, version_id: str, doc_id: str, version_num: int, effective_from: str, effective_to: str = None, status: str = "Active", supersedes_id: str = None) -> None:
        # If this supersedes a previous version, mark the previous version as 'Superseded'
        conn = self.get_connection()
        with conn.cursor() as cur:
            if supersedes_id:
                cur.execute(
                    "UPDATE document_versions SET status = 'Superseded', effective_to = %s WHERE version_id = %s;",
                    (effective_from, supersedes_id)
                )
            cur.execute(
                """
                INSERT INTO document_versions (version_id, document_id, version_number, effective_from, effective_to, status, supersedes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (version_id) DO NOTHING;
                """,
                (version_id, doc_id, version_num, effective_from, effective_to, status, supersedes_id)
            )
            conn.commit()

    def insert_chunks_and_embeddings(self, chunks_data: List[Dict[str, Any]], embeddings_data: List[Tuple[str, str, List[float]]]) -> None:
        """
        chunks_data list of dicts: {'chunk_id', 'version_id', 'section_name', 'clause_name', 'page_number', 'chunk_text'}
        embeddings_data list of tuples: (embedding_id, chunk_id, embedding_vector)
        """
        conn = self.get_connection()
        with conn.cursor() as cur:
            # Bulk insert chunks
            chunk_query = """
                INSERT INTO chunks (chunk_id, version_id, section_name, clause_name, page_number, chunk_text)
                VALUES %s ON CONFLICT (chunk_id) DO NOTHING;
            """
            chunk_values = [
                (c['chunk_id'], c['version_id'], c['section_name'], c['clause_name'], c['page_number'], c['chunk_text'])
                for c in chunks_data
            ]
            execute_values(cur, chunk_query, chunk_values)

            # Bulk insert embeddings
            emb_query = """
                INSERT INTO embeddings (embedding_id, chunk_id, embedding)
                VALUES %s ON CONFLICT (embedding_id) DO NOTHING;
            """
            # Format vector as string like '[0.1, 0.2, ...]' for pgvector
            emb_values = [
                (e[0], e[1], f"[{','.join(map(str, e[2]))}]")
                for e in embeddings_data
            ]
            execute_values(cur, emb_query, emb_values)
            conn.commit()

    def hybrid_search(self, query_text: str, query_vector: List[float], limit: int = 30) -> List[Dict[str, Any]]:
        """
        Performs Hybrid Search combining Vector Search and Full-Text Search via Reciprocal Rank Fusion (RRF).
        """
        # 1. Semantic Search (pgvector HNSW)
        semantic_query = """
            SELECT
                dc.id::text AS chunk_id,
                COALESCE(dc.metadata->>'section_name', '') AS section_name,
                COALESCE(dc.metadata->>'clause_name', '') AS clause_name,
                NULLIF(dc.metadata->>'page_number', '')::int AS page_number,
                dc.content AS chunk_text,
                rd.title AS doc_title,
                COALESCE(rd.source_file, dc.metadata->>'source', '') AS doc_source,
                COALESCE(dc.metadata->>'version_number', '1')::int AS version_number,
                NULL::timestamp AS effective_from,
                1 - (dc.embedding <=> %s::vector) AS similarity
            FROM public.document_chunks dc
            JOIN regulatory_documents rd ON dc.document_id = rd.id
            WHERE LOWER(COALESCE(rd.status, 'active')) = 'active'
              AND dc.embedding IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s;
        """
        # Format vector
        vector_str = f"[{','.join(map(str, query_vector))}]"
        semantic_results = self.execute_query(semantic_query, (vector_str, limit))

        # 2. Keyword Search (Postgres FTS)
        keyword_query = """
                        SELECT
                                dc.id::text AS chunk_id,
                                COALESCE(dc.metadata->>'section_name', '') AS section_name,
                                COALESCE(dc.metadata->>'clause_name', '') AS clause_name,
                                NULLIF(dc.metadata->>'page_number', '')::int AS page_number,
                                dc.content AS chunk_text,
                                rd.title AS doc_title,
                                COALESCE(rd.source_file, dc.metadata->>'source', '') AS doc_source,
                                COALESCE(dc.metadata->>'version_number', '1')::int AS version_number,
                                NULL::timestamp AS effective_from,
                                ts_rank_cd(to_tsvector('english', dc.content), plainto_tsquery('english', %s)) AS rank
                        FROM public.document_chunks dc
                        JOIN regulatory_documents rd ON dc.document_id = rd.id
                        WHERE to_tsvector('english', dc.content) @@ plainto_tsquery('english', %s)
                            AND LOWER(COALESCE(rd.status, 'active')) = 'active'
            ORDER BY rank DESC
            LIMIT %s;
        """
        keyword_results = self.execute_query(keyword_query, (query_text, query_text, limit))

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF score = sum( 1 / (60 + rank) )
        rrf_scores: Dict[str, float] = {}
        merged_chunks: Dict[str, Dict[str, Any]] = {}

        # Process Semantic Results
        for rank, res in enumerate(semantic_results, start=1):
            chunk_id = res['chunk_id']
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (60.0 + rank))
            if chunk_id not in merged_chunks:
                merged_chunks[chunk_id] = res

        # Process Keyword Results
        for rank, res in enumerate(keyword_results, start=1):
            chunk_id = res['chunk_id']
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (60.0 + rank))
            if chunk_id not in merged_chunks:
                merged_chunks[chunk_id] = res

        # Sort merged chunks by RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        
        final_results = []
        for cid in sorted_chunk_ids[:limit]:
            chunk_data = merged_chunks[cid]
            chunk_data['rrf_score'] = rrf_scores[cid]
            final_results.append(chunk_data)

        return final_results
