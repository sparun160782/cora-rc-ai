"""
Compliance reports endpoints.
Generates weekly/monthly reports via the agentic backend.
"""
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from cora_rc_ai.backend_api.core.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateReportRequest(BaseModel):
    report_type: str = "weekly"   # weekly | monthly | custom
    from_date: str                 # ISO date string
    to_date: str
    jurisdiction: Optional[str] = None
    include_audit_trail: bool = True
    stream: bool = False


@router.post("/generate", summary="Generate a compliance report")
async def generate_report(request: Request, payload: GenerateReportRequest):
    """Generate a structured compliance report for a given period."""
    agent_message = (
        f"Generate a {payload.report_type} compliance report for FinServ Global "
        f"covering {payload.from_date} to {payload.to_date}."
        f"{' Focus on ' + payload.jurisdiction + ' jurisdiction.' if payload.jurisdiction else ''}"
        f" Include: summary statistics, risk distribution, flagged transactions, "
        f"regulation violations, remediation recommendations, and an audit trail appendix."
    )

    if payload.stream:
        async def forward_stream():
            async with request.app.state.http_client.stream(
                "POST",
                "/v1/agent/chat/stream",
                json={"message": agent_message, "user_id": "report_system"},
            ) as resp:
                async for chunk in resp.aiter_text():
                    yield chunk
        return StreamingResponse(forward_stream(), media_type="text/event-stream")

    try:
        resp = await request.app.state.http_client.post(
            "/v1/agent/chat",
            json={"message": agent_message, "user_id": "report_system"},
        )
        resp.raise_for_status()
        result = resp.json()
        report_content = result.get("response", "")
        report_id = str(uuid.uuid4())
        generated_at = datetime.utcnow().isoformat()

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO compliance_reports
                    (id, report_type, from_date, to_date, jurisdiction, content, generated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                report_id,
                payload.report_type,
                payload.from_date,
                payload.to_date,
                payload.jurisdiction,
                report_content,
                generated_at,
            )

        return {
            "report_id": report_id,
            "report_type": payload.report_type,
            "from_date": payload.from_date,
            "to_date": payload.to_date,
            "content": report_content,
            "generated_at": generated_at,
        }
    except Exception as e:
        logger.error("Report generation error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/", summary="List generated compliance reports")
async def list_reports(limit: int = 20, offset: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, report_type, from_date, to_date,
                   jurisdiction, generated_at
            FROM compliance_reports
            ORDER BY generated_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return {"reports": [dict(r) for r in rows], "count": len(rows)}


@router.get("/{report_id}", summary="Get a specific compliance report")
async def get_report(report_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM compliance_reports WHERE id = $1",
            report_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(row)
