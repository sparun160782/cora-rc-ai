"""
RAG Document Ingestion Pipeline.
Parses PDF/DOCX/TXT regulatory documents, chunks them, embeds via BGE,
and upserts into PostgreSQL pgvector store.
"""
import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Generator
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncpg

logger = logging.getLogger(__name__)

# ── Chunking config ────────────────────────────────────────────────────────────
CHUNK_SIZE = 512          # tokens ≈ characters / 4
CHUNK_OVERLAP = 64
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# ── Utility: simple text chunker ──────────────────────────────────────────────
#def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
#    """Splits text into overlapping word-boundary chunks."""
#    words = text.split()
#    chunks = []
#    start = 0
#    while start < len(words):
#        end = min(start + chunk_size, len(words))
#        chunk = " ".join(words[start:end])
#        chunks.append(chunk)
#        start += chunk_size - overlap
#    return chunks

def _chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> list[str]:
    """Splits text using recursive paragraph & sentence splits on character lengths."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
        is_separator_regex=False,
    )
    return splitter.split_text(text)

# ── Utility: extract text from file ───────────────────────────────────────────
def _extract_text(filepath: Path) -> str:
    suffix = filepath.suffix.lower()
    if suffix == ".txt" or suffix == ".md":
        return filepath.read_text(encoding="utf-8", errors="ignore")
    elif suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except ImportError:
            logger.warning("pdfplumber not installed. Skipping PDF: %s", filepath)
            return ""
    elif suffix == ".docx":
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed. Skipping DOCX: %s", filepath)
            return ""
    return ""

# ── Utility: compute doc hash for deduplication ───────────────────────────────
def _file_hash(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# ── Main ingestion function ────────────────────────────────────────────────────
async def ingest_documents(
    source_dir: str,
    db_url: str,
    jurisdiction: str = "GLOBAL",
    doc_type: str = "regulation",
    batch_size: int = 32,
):
    """
    Walk source_dir, extract text, chunk, embed, and upsert into pgvector.
    """
    from models.embeddings_model import EmbeddingsModel

    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    embedder = EmbeddingsModel()
    conn = await asyncpg.connect(db_url)

    try:
        files = [
            f for f in source_path.rglob("*")
            if f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        logger.info("Found %d documents to ingest from %s", len(files), source_dir)

        for filepath in files:
            file_hash = _file_hash(filepath)

            # Deduplication check
            existing = await conn.fetchval(
                "SELECT 1 FROM regulatory_documents WHERE source_hash = $1 LIMIT 1",
                file_hash,
            )
            if existing:
                logger.info("Skipping already-ingested file: %s", filepath.name)
                continue

            # Insert document record
            doc_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO regulatory_documents
                    (id, title, doc_type, jurisdiction, source_file, source_hash, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'processing')
                ON CONFLICT (source_hash) DO NOTHING
                """,
                doc_id,
                filepath.stem.replace("_", " ").title(),
                doc_type,
                jurisdiction,
                str(filepath),
                file_hash,
            )

            # Extract and chunk
            text = _extract_text(filepath)
            if not text.strip():
                logger.warning("Empty text from: %s", filepath.name)
                continue

            chunks = _chunk_text(text)
            logger.info("Processing %s → %d chunks", filepath.name, len(chunks))

            # Embed in batches
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                vectors = embedder.encode(batch)

                for j, (chunk_text, vector) in enumerate(zip(batch, vectors)):
                    chunk_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO document_chunks
                            (id, document_id, chunk_index, content, embedding, metadata)
                        VALUES ($1, $2, $3, $4, $5::vector, $6)
                        ON CONFLICT DO NOTHING
                        """,
                        chunk_id,
                        doc_id,
                        i + j,
                        chunk_text,
                        json.dumps(vector.tolist()),
                        json.dumps({"source": filepath.name, "chunk": i + j}),
                    )

            # Mark document as processed
            await conn.execute(
                "UPDATE regulatory_documents SET status = 'active' WHERE id = $1",
                doc_id,
            )
            logger.info("Ingested: %s (%d chunks)", filepath.name, len(chunks))

    finally:
        await conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest regulatory documents into CORA vector store")
    parser.add_argument("--source-dir", required=True, help="Directory containing regulatory documents")
    parser.add_argument("--jurisdiction", default="GLOBAL", help="Jurisdiction code (RBI, MIFID, BASEL, GLOBAL)")
    parser.add_argument("--doc-type", default="regulation", help="Document type")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"), help="PostgreSQL connection URL")
    args = parser.parse_args()

    if not args.db_url:
        raise ValueError("DATABASE_URL environment variable or --db-url must be set")

    asyncio.run(
        ingest_documents(
            source_dir=args.source_dir,
            db_url=args.db_url,
            jurisdiction=args.jurisdiction,
            doc_type=args.doc_type,
        )
    )
