"""
Regulatory knowledge base query endpoints.
"""
import json
import logging
import uuid
from pathlib import Path
from typing import Optional
from datetime import date

from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cora_rc_ai.backend_agentic.models.embeddings_model import EmbeddingsModel
from cora_rc_ai.backend_agentic.rag.ingestion.ingest_pipeline import _chunk_text, _extract_text, _file_hash
from cora_rc_ai.backend_api.core.config import settings
from cora_rc_ai.backend_api.core.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()

PRELOADED_TOPICS = [
    {"name": "CDD", "topic_type": "Core", "description": "Customer Due Diligence", "is_mandatory": True},
    {"name": "Monitoring", "topic_type": "Core", "description": "Transaction Monitoring", "is_mandatory": True},
    {"name": "BO", "topic_type": "Core", "description": "Beneficial Ownership", "is_mandatory": True},
    {"name": "Loan Transfer", "topic_type": "Extended", "description": "Loan transfer conditions", "is_mandatory": False},
    {"name": "Stressed Assets", "topic_type": "Extended", "description": "Stressed asset handling", "is_mandatory": False},
    {"name": "Capital Adequacy", "topic_type": "Core", "description": "Capital adequacy requirements", "is_mandatory": False},
]

PERSONAS = [
    {
        "id": "compliance_officer",
        "name": "Compliance Officer",
        "action": "Day-to-day checking",
        "needs": ["Fast answers", "Citations"],
    },
    {
        "id": "compliance_head",
        "name": "Compliance Head",
        "action": "Oversight and reporting",
        "needs": ["Summary reports", "Risk trends"],
    },
    {
        "id": "internal_auditor",
        "name": "Internal Auditor",
        "action": "Post-review",
        "needs": ["Audit trail", "Evidence and sources"],
    },
]


class RegulationQueryRequest(BaseModel):
    question: str
    jurisdiction: Optional[str] = None   # RBI, MIFID, BASEL, FATF, GLOBAL
    session_id: Optional[str] = None
    user_id: str = "default_user"
    persona: Optional[str] = None
    stream: bool = False


async def _upsert_chat_session(
    conn,
    session_id: str,
    user_id: str,
    persona: Optional[str],
    title_seed: str,
    preview: Optional[str] = None,
) -> None:
    title = title_seed.strip()[:120]
    await conn.execute(
        """
        INSERT INTO chat_sessions (id, user_id, persona, title, last_message_preview)
        VALUES ($1::uuid, $2, $3, $4, $5)
        ON CONFLICT (id)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            persona = COALESCE(EXCLUDED.persona, chat_sessions.persona),
            title = COALESCE(chat_sessions.title, EXCLUDED.title),
            last_message_preview = COALESCE(EXCLUDED.last_message_preview, chat_sessions.last_message_preview),
            updated_at = CURRENT_TIMESTAMP
        """,
        session_id,
        user_id,
        persona,
        title,
        (preview or title_seed)[:240],
    )


async def _append_chat_message(
    conn,
    session_id: str,
    role: str,
    content: str,
    citations: Optional[list] = None,
    metadata: Optional[dict] = None,
) -> None:
    
    token_count = (metadata or {}).get("token_count")
    response_time_ms = (metadata or {}).get("response_time_ms")

    await conn.execute(
        """
        INSERT INTO chat_messages (
            session_id, role, content, citations, token_count, response_time_ms
        )
        VALUES ($1, $2, $3, $4::jsonb, $5, $6)
        """,
        session_id,
        role,
        content,
        json.dumps(citations or []),
        token_count,
        response_time_ms,
    )
    await conn.execute(
        """
        UPDATE chat_sessions
        SET updated_at = CURRENT_TIMESTAMP,
            last_message_preview = $2
        WHERE id = $1::uuid
        """,
        session_id,
        content[:240],
    )


async def _ensure_taxonomy(conn, payload: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    framework_id = None
    domain_id = None
    category_id = None

    framework_name = payload.get("framework_name")
    if framework_name:
        framework_id = await conn.fetchval(
            """
            INSERT INTO frameworks (name, description, created_by, version)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (name)
            DO UPDATE SET
                description = COALESCE(EXCLUDED.description, frameworks.description),
                created_by = COALESCE(EXCLUDED.created_by, frameworks.created_by),
                version = COALESCE(EXCLUDED.version, frameworks.version)
            RETURNING id
            """,
            framework_name,
            payload.get("framework_description"),
            payload.get("framework_created_by"),
            payload.get("framework_version"),
        )

    domain_name = payload.get("domain_name")
    if framework_id and domain_name:
        domain_id = await conn.fetchval(
            """
            INSERT INTO domains (framework_id, name, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (framework_id, name)
            DO UPDATE SET description = COALESCE(EXCLUDED.description, domains.description)
            RETURNING id
            """,
            framework_id,
            domain_name,
            payload.get("domain_description"),
        )

    category_name = payload.get("category_name")
    if domain_id and category_name:
        category_id = await conn.fetchval(
            """
            INSERT INTO categories (domain_id, name, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (domain_id, name)
            DO UPDATE SET description = COALESCE(EXCLUDED.description, categories.description)
            RETURNING id
            """,
            domain_id,
            category_name,
            payload.get("category_description"),
        )

    return framework_id, domain_id, category_id


async def _ensure_topics(conn, topics: list[str]) -> list[str]:
    topic_ids: list[str] = []
    for topic_name in topics:
        topic_id = await conn.fetchval(
            """
            INSERT INTO topics (name)
            VALUES ($1)
            ON CONFLICT (name)
            DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            topic_name,
        )
        topic_ids.append(topic_id)
    return topic_ids


async def _ingest_uploaded_document(conn, document_id: str, file_path: Path, original_name: str) -> int:
    text = _extract_text(file_path)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Uploaded file does not contain extractable text")

    chunks = _chunk_text(text)
    embedder = EmbeddingsModel()

    for index, chunk_text in enumerate(chunks):
        embedding = embedder.get_embedding(chunk_text)
        await conn.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_index, content, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            document_id,
            index,
            chunk_text,
            embedding,
            json.dumps({"source": original_name, "chunk_index": index}),
        )

    return len(chunks)


def _build_jurisdiction_context(jurisdiction: Optional[str]) -> str:
    """
    Shape the jurisdiction instruction to avoid hallucination bias.
    - Specific single regulator (RBI, MIFID, FATF, BASEL) -> restrict to that source.
    - GLOBAL or absent -> broad search but prioritize relevance, not inference.
    """
    if not jurisdiction or jurisdiction.upper() == "GLOBAL":
        return (
            " Search across all available jurisdictions (RBI, Basel III, MiFID II, FATF). "
            "Return only verbatim clauses found in the knowledge base, not a paraphrased summary. "
            "Do NOT infer or fabricate regulatory text."
        )
    # Single-jurisdiction — restrict tightly
    regulator_map = {
        "RBI": "RBI (Reserve Bank of India)",
        "MIFID": "MiFID II (EU)",
        "MIFID2": "MiFID II (EU)",
        "FATF": "FATF",
        "BASEL": "Basel III",
        "BASEL3": "Basel III",
    }
    label = regulator_map.get(jurisdiction.upper(), jurisdiction)
    return (
        f" Restrict your answer strictly to {label} sources found in the knowledge base. "
        "Do NOT reference other jurisdictions unless the user explicitly requests "
        "cross-jurisdiction comparison. "
        "Return only verbatim clause excerpts from the knowledge base, with exact document title, "
        "section, clause, and page if available. Do NOT paraphrase or summarize. "
        "Do NOT infer or fabricate regulatory text."
    )


@router.post("/query", summary="Query the regulatory knowledge base")
async def query_regulations(request: Request, payload: RegulationQueryRequest):
    """Ask a natural language question about compliance regulations."""
    jurisdiction_context = _build_jurisdiction_context(payload.jurisdiction)
    agent_message = payload.question + jurisdiction_context

    if payload.stream:
        async def forward_stream():
            pool = await get_pool()
            active_session_id = payload.session_id
            full_content = ""
            fallback_message = (
                "I could not generate a final response from the model. "
                "Please try again."
            )
            async with request.app.state.http_client.stream(
                "POST",
                "/v1/agent/chat/stream",
                json={
                    "message": agent_message,
                    "session_id": payload.session_id,
                    "user_id": payload.user_id,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = json.loads(line[6:])
                    if data.get("type") == "session_id":
                        active_session_id = data.get("session_id")
                        async with pool.acquire() as conn:
                            await _upsert_chat_session(
                                conn,
                                active_session_id,
                                payload.user_id,
                                payload.persona,
                                payload.question,
                                payload.question,
                            )
                            await _append_chat_message(
                                conn,
                                active_session_id,
                                "user",
                                payload.question,
                                metadata={"jurisdiction": payload.jurisdiction},
                            )
                    elif data.get("type") == "token":
                        full_content += data.get("content", "")
                    elif data.get("type") == "done" and active_session_id:
                        if not full_content.strip():
                            # Guard against tool-only or failed model turns that emit
                            # no final token content, so UI never shows a blank bubble.
                            full_content = fallback_message
                            yield f"data: {json.dumps({'type': 'token', 'content': full_content, 'author': 'compliance_agent'}, ensure_ascii=False)}\n\n"
                        async with pool.acquire() as conn:
                            await _append_chat_message(
                                conn,
                                active_session_id,
                                "agent",
                                full_content,
                                metadata={"jurisdiction": payload.jurisdiction, "persona": payload.persona},
                            )

                    #yield f"data: {json.dumps(data)}\n\n"
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        #return StreamingResponse(forward_stream(), media_type="text/event-stream")
        return StreamingResponse(
                forward_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
        )

    try:
        pool = await get_pool()
        resp = await request.app.state.http_client.post(
            "/v1/agent/chat",
            json={
                "message": agent_message,
                "session_id": payload.session_id,
                "user_id": payload.user_id,
            },
        )
        resp.raise_for_status()
        result = resp.json()
        async with pool.acquire() as conn:
            await _upsert_chat_session(
                conn,
                result.get("session_id"),
                payload.user_id,
                payload.persona,
                payload.question,
                result.get("response", ""),
            )
            await _append_chat_message(
                conn,
                result.get("session_id"),
                "user",
                payload.question,
                metadata={"jurisdiction": payload.jurisdiction},
            )
            await _append_chat_message(
                conn,
                result.get("session_id"),
                "agent",
                result.get("response", ""),
                metadata={"jurisdiction": payload.jurisdiction, "persona": payload.persona},
            )
        return {
            "question": payload.question,
            "jurisdiction": payload.jurisdiction,
            "answer": result.get("response", ""),
            "session_id": result.get("session_id"),
        }
    except Exception as e:
        logger.error("Regulation query error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/search", summary="Search regulations by keyword")
async def search_regulations(
    q: str = Query(..., description="Search query"),
    jurisdiction: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Full-text search across ingested regulatory documents."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        jurisdiction_filter = ""
        params = [f"%{q}%", limit]
        if jurisdiction:
            jurisdiction_filter = "AND rd.jurisdiction = $3"
            params.append(jurisdiction)

        rows = await conn.fetch(
            f"""
            SELECT dc.id, dc.content, dc.chunk_index,
                   rd.title, rd.jurisdiction, rd.doc_type
            FROM document_chunks dc
            JOIN regulatory_documents rd ON dc.document_id = rd.id
            WHERE dc.content ILIKE $1
                  {jurisdiction_filter}
            ORDER BY dc.chunk_index
            LIMIT $2
            """,
            *params,
        )
    return {
        "query": q,
        "results": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/documents", summary="List ingested regulatory documents")
async def list_documents(
    jurisdiction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT rd.id,
                   rd.title,
                   rd.doc_type,
                   rd.jurisdiction,
                   rd.status,
                   rd.created_at,
                   rd.regulatory_body,
                   rd.applicable_entity,
                   rd.version_year,
                   rd.file_size_bytes,
                   rd.effective_date,
                   cf.name AS framework_name,
                   cd.name AS domain_name,
                   cc.name AS category_name,
                   COALESCE(COUNT(dc.id), 0) AS chunk_count,
                   COALESCE(ARRAY_REMOVE(ARRAY_AGG(DISTINCT ct.name), NULL), '{}') AS mapped_topics
            FROM regulatory_documents rd
            LEFT JOIN frameworks cf ON cf.id = rd.framework_id
            LEFT JOIN domains cd ON cd.id = rd.domain_id
            LEFT JOIN categories cc ON cc.id = rd.category_id
            LEFT JOIN document_topic_mappings dtm ON dtm.document_id = rd.id
            LEFT JOIN topics ct ON ct.id = dtm.topic_id
            LEFT JOIN document_chunks dc ON dc.document_id = rd.id
            WHERE ($1::text IS NULL OR rd.status = $1)
              AND ($2::text IS NULL OR rd.jurisdiction = $2)
            GROUP BY rd.id, cf.name, cd.name, cc.name
            ORDER BY rd.created_at DESC
            """,
            status,
            jurisdiction,
        )
    return {"documents": [dict(r) for r in rows], "count": len(rows)}


@router.get("/taxonomy", summary="Return document taxonomy and preloaded topics")
async def get_taxonomy():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 1. Preload Topics
        for topic in PRELOADED_TOPICS:
            await conn.execute(
                """
                INSERT INTO topics (name, topic_type, description, is_mandatory)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name)
                DO UPDATE SET
                    topic_type = EXCLUDED.topic_type,
                    description = COALESCE(EXCLUDED.description, topics.description),
                    is_mandatory = EXCLUDED.is_mandatory
                """,
                topic["name"],
                topic["topic_type"],
                topic["description"],
                topic["is_mandatory"],
            )

         # 2. Dynamic Seeding for Framework, Domains, and Categories
        default_fw_id = await conn.fetchval(
            """
            INSERT INTO frameworks (name, description, version, created_by)
            VALUES ('RBI Framework', 'Reserve Bank of India Regulatory Framework', 'v1', 'system')
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        )
        if default_fw_id:
            # Domain 1 & Category 1
            dom1_id = await conn.fetchval(
                """
                INSERT INTO domains (framework_id, name, description)
                VALUES ($1, 'Compliance & Financial Crime Control', 'Anti-Money Laundering, KYC, and financial crime requirements')
                ON CONFLICT (framework_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                default_fw_id,
            )
            if dom1_id:
                await conn.execute(
                    """
                    INSERT INTO categories (domain_id, name, description)
                    VALUES ($1, 'AML_KYC', 'Anti-Money Laundering & Know Your Customer Circulars')
                    ON CONFLICT (domain_id, name) DO UPDATE SET name = EXCLUDED.name
                    """,
                    dom1_id,
                )

            # Domain 2 & Category 2
            dom2_id = await conn.fetchval(
                """
                INSERT INTO domains (framework_id, name, description)
                VALUES ($1, 'Credit Risk & Loan Lifecycle Regulations', 'Loan exposure, retail transfer, and stressed assets management')
                ON CONFLICT (framework_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                default_fw_id,
            )
            if dom2_id:
                await conn.execute(
                    """
                    INSERT INTO categories (domain_id, name, description)
                    VALUES ($1, 'Loan Transfer & Asset Lifecycle', 'Rules on transfer of loan exposures and pricing policies')
                    ON CONFLICT (domain_id, name) DO UPDATE SET name = EXCLUDED.name
                    """,
                    dom2_id,
                )

            # Domain 3 & Category 3
            dom3_id = await conn.fetchval(
                """
                INSERT INTO domains (framework_id, name, description)
                VALUES ($1, 'NBFC Prudential / Regulatory Framework', 'Prudential norms, capital requirements, and systemic risks for NBFCs')
                ON CONFLICT (framework_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                default_fw_id,
            )
            if dom3_id:
                await conn.execute(
                    """
                    INSERT INTO categories (domain_id, name, description)
                    VALUES ($1, 'Core NBFC Regulations', 'Master directions for non-deposit taking systematically important NBFCs')
                    ON CONFLICT (domain_id, name) DO UPDATE SET name = EXCLUDED.name
                    """,
                    dom3_id,
                )

        # 3. Retrieve Records
        frameworks = await conn.fetch(
            "SELECT id, name, description, created_by, version FROM frameworks ORDER BY name"
        )
        domains = await conn.fetch(
            """
            SELECT cd.id, cd.framework_id, cd.name, cd.description, cf.name AS framework_name
            FROM domains cd
            JOIN frameworks cf ON cf.id = cd.framework_id
            ORDER BY cf.name, cd.name
            """
        )
        categories = await conn.fetch(
            """
            SELECT cc.id, cc.domain_id, cc.name, cc.description, cd.name AS domain_name
            FROM categories cc
            JOIN domains cd ON cd.id = cc.domain_id
            ORDER BY cd.name, cc.name
            """
        )
        topics = await conn.fetch(
            "SELECT id, name, topic_type, description, is_mandatory FROM topics ORDER BY name"
        )

        # Convert fetched rows to real python dicts
        fw_list = [dict(row) for row in frameworks]
        dm_list = [dict(row) for row in domains]
        cat_list = [dict(row) for row in categories]
        top_list = [dict(row) for row in topics]

        # Convert UUIDs to strings to guarantee flawless JSON serialization
        for fw in fw_list:
            fw["id"] = str(fw["id"])
        
        for dm in dm_list:
            dm["id"] = str(dm["id"])
            dm["framework_id"] = str(dm["framework_id"])
            
        for cat in cat_list:
            cat["id"] = str(cat["id"])
            cat["domain_id"] = str(cat["domain_id"])

        for top in top_list:
            top["id"] = str(top["id"])

        # Construct nested taxonomy tree
        categories_by_domain = {}
        for cat in cat_list:
            cat["topics"] = top_list  # Expose available topics inside categories
            d_id = cat["domain_id"]
            if d_id not in categories_by_domain:
                categories_by_domain[d_id] = []
            categories_by_domain[d_id].append(cat)

        domains_by_framework = {}
        for dm in dm_list:
            d_id = dm["id"]
            dm["categories"] = categories_by_domain.get(d_id, [])
            fw_id = dm["framework_id"]
            if fw_id not in domains_by_framework:
                domains_by_framework[fw_id] = []
            domains_by_framework[fw_id].append(dm)

        for fw in fw_list:
            fw_id = fw["id"]
            fw["domains"] = domains_by_framework.get(fw_id, [])

    return {
        "frameworks": fw_list,
        "domains": dm_list,
        "categories": cat_list,
        "topics": top_list,
        "personas": PERSONAS,
    }


@router.post("/documents/upload", summary="Upload and ingest a regulatory document")
async def upload_document(
    file: UploadFile = File(...),
    framework_name: str = Form(...),
    domain_name: str = Form(...),
    category_name: str = Form(...),
    document_name: str = Form(...),
    jurisdiction: str = Form("GLOBAL"),
    document_type: str = Form("regulation"),
    regulatory_body: Optional[str] = Form(None),
    applicable_entity: Optional[str] = Form(None),
    version_year: Optional[str] = Form(None),
    framework_description: Optional[str] = Form(None),
    framework_created_by: Optional[str] = Form(None),
    framework_version: Optional[str] = Form(None),
    domain_description: Optional[str] = Form(None),
    category_description: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    section_reference: Optional[str] = Form(None),
    risk_level: Optional[str] = Form(None),
    compliance_type: Optional[str] = Form(None),
    entity_type: Optional[str] = Form(None),
    keywords: str = Form(""),
    mapped_topics: str = Form("[]"),
    uploaded_by: str = Form("default_user"),
):
    upload_root = Path(settings.DOCUMENT_UPLOAD_DIR)
    upload_root.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    destination = upload_root / f"{file_id}_{file.filename}"
    destination.write_bytes(await file.read())
    file_hash = _file_hash(destination)

    # Convert frontend effective_date string to datetime.date object (or None if empty)
    parsed_effective_date = None
    if effective_date and effective_date.strip():
        try:
            parsed_effective_date = date.fromisoformat(effective_date.strip())
        except ValueError:
            logger.warning("Failed to parse effective_date string: %s", effective_date)

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, title FROM regulatory_documents WHERE source_hash = $1",
            file_hash,
        )
        if existing is not None:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail=f"Document already exists: {existing['title']}")

        framework_id, domain_id, category_id = await _ensure_taxonomy(
            conn,
            {
                "framework_name": framework_name,
                "framework_description": framework_description,
                "framework_created_by": framework_created_by,
                "framework_version": framework_version,
                "domain_name": domain_name,
                "domain_description": domain_description,
                "category_name": category_name,
                "category_description": category_description,
            },
        )

        document_id = await conn.fetchval(
            """
            INSERT INTO regulatory_documents (
                title, doc_type, jurisdiction, source_file, source_hash, status,
                framework_id, domain_id, category_id,
                regulatory_body, applicable_entity, version_year,
                effective_date, section_reference, risk_level, compliance_type,
                entity_type, description, keywords, file_size_bytes, uploaded_by, metadata
            )
            VALUES (
                $1, $2, $3, $4, $5, 'processing',
                $6, $7, $8,
                $9, $10, $11,
                $12::date, $13, $14, $15,
                $16, $17, $18, $19, $20, $21::jsonb
            )
            RETURNING id
            """,
            document_name,
            document_type,
            jurisdiction,
            str(destination),
            file_hash,
            framework_id,
            domain_id,
            category_id,
            regulatory_body,
            applicable_entity,
            version_year,
            parsed_effective_date,  # <-- Pass the parsed Python date object here
            section_reference,
            risk_level,
            compliance_type,
            entity_type,
            description,
            [keyword.strip() for keyword in keywords.split(",") if keyword.strip()],
            destination.stat().st_size,
            uploaded_by,
            json.dumps({"original_filename": file.filename}),
        )

        topic_names = [item.strip() for item in json.loads(mapped_topics) if str(item).strip()]
        topic_ids = await _ensure_topics(conn, topic_names)
        for topic_id in topic_ids:
            await conn.execute(
                """
                INSERT INTO document_topic_mappings (document_id, topic_id)
                VALUES ($1, $2)
                ON CONFLICT (document_id, topic_id) DO NOTHING
                """,
                document_id,
                topic_id,
            )

        try:
            chunk_count = await _ingest_uploaded_document(conn, document_id, destination, file.filename or document_name)
            await conn.execute(
                """
                UPDATE regulatory_documents
                SET status = 'active', processed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                document_id,
            )
        except Exception as exc:
            await conn.execute(
                """
                UPDATE regulatory_documents
                SET status = 'failed', processing_error = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                document_id,
                str(exc),
            )
            raise

    return {
        "id": document_id,
        "title": document_name,
        "status": "active",
        "chunk_count": chunk_count,
    }


@router.delete("/documents/{document_id}", summary="Delete a regulatory document")
async def delete_document(document_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT source_file FROM regulatory_documents WHERE id = $1",
            document_id,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Document not found")

        await conn.execute("DELETE FROM regulatory_documents WHERE id = $1", document_id)

    if record.get("source_file"):
        Path(record["source_file"]).unlink(missing_ok=True)

    return {"deleted": True, "document_id": document_id}
