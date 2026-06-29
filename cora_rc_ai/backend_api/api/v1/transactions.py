"""
Transaction screening endpoints.
Submits transactions to the agentic backend for risk assessment.
"""
import uuid
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from cora_rc_ai.backend_api.core.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────
class TransactionScreenRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    sender_account: str
    receiver_account: str
    sender_country: str
    receiver_country: str
    transaction_type: str
    customer_risk_tier: str = "medium"
    is_pep: bool = False
    is_sanctioned: bool = False
    notes: Optional[str] = None


class TransactionScreenResponse(BaseModel):
    screening_id: str
    transaction_id: str
    risk_rating: str
    confidence: float
    flagged_violations: list[str]
    required_actions: list[str]
    applicable_regulations: list[str]
    citations: list[dict]
    reasoning_summary: str
    screened_at: str


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/screen", response_model=TransactionScreenResponse, summary="Screen a transaction")
async def screen_transaction(request: Request, payload: TransactionScreenRequest):
    """
    Submit a transaction for AI-powered compliance risk assessment.
    Routes to the Agentic backend's risk_agent for full analysis.
    """
    agent_message = (
        f"Please screen the following transaction for compliance risks:\n"
        f"{json.dumps(payload.model_dump(), indent=2)}\n\n"
        f"Provide a complete risk assessment with applicable regulations, "
        f"flagged violations, required actions, and cited sources."
    )

    try:
        resp = await request.app.state.http_client.post(
            "/v1/agent/chat",
            json={"message": agent_message, "user_id": "compliance_system"},
        )
        resp.raise_for_status()
        agent_result = resp.json()
        raw_response = agent_result.get("response", "{}")

        # Try to parse structured JSON from agent response
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            # Fallback: wrap the raw text
            parsed = {
                "risk_rating": "REVIEW",
                "confidence": 0.5,
                "flagged_violations": [],
                "required_actions": ["Manual review required"],
                "applicable_regulations": [],
                "citations": [],
                "reasoning_summary": raw_response,
            }

        screening_id = str(uuid.uuid4())
        screened_at = datetime.utcnow().isoformat()

        # Persist result to DB
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO transaction_screenings
                    (id, transaction_id, risk_rating, confidence,
                     flagged_violations, required_actions, applicable_regulations,
                     citations, reasoning_summary, screened_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                screening_id,
                payload.transaction_id,
                parsed.get("risk_rating", "REVIEW"),
                parsed.get("confidence", 0.5),
                json.dumps(parsed.get("flagged_violations", [])),
                json.dumps(parsed.get("required_actions", [])),
                json.dumps(parsed.get("applicable_regulations", [])),
                json.dumps(parsed.get("citations", [])),
                parsed.get("reasoning_summary", ""),
                screened_at,
            )

        return TransactionScreenResponse(
            screening_id=screening_id,
            transaction_id=payload.transaction_id,
            risk_rating=parsed.get("risk_rating", "REVIEW"),
            confidence=parsed.get("confidence", 0.5),
            flagged_violations=parsed.get("flagged_violations", []),
            required_actions=parsed.get("required_actions", []),
            applicable_regulations=parsed.get("applicable_regulations", []),
            citations=parsed.get("citations", []),
            reasoning_summary=parsed.get("reasoning_summary", ""),
            screened_at=screened_at,
        )

    except httpx.HTTPError as e:
        logger.error("Agent backend error: %s", e)
        raise HTTPException(status_code=502, detail=f"Agentic backend unreachable: {str(e)}")


@router.post("/screen/stream", summary="Stream transaction screening (SSE)")
async def screen_transaction_stream(request: Request, payload: TransactionScreenRequest):
    """SSE streaming version of transaction screening."""
    agent_message = (
        f"Screen this transaction for compliance risks:\n"
        f"{json.dumps(payload.model_dump(), indent=2)}"
    )

    async def forward_stream():
        async with request.app.state.http_client.stream(
            "POST",
            "/v1/agent/chat/stream",
            json={"message": agent_message, "user_id": "compliance_system"},
        ) as resp:
            async for chunk in resp.aiter_text():
                yield chunk

    return StreamingResponse(forward_stream(), media_type="text/event-stream")


@router.get("/{transaction_id}/history", summary="Get screening history for a transaction")
async def get_screening_history(transaction_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, risk_rating, confidence, flagged_violations,
                   required_actions, screened_at
            FROM transaction_screenings
            WHERE transaction_id = $1
            ORDER BY screened_at DESC
            LIMIT 50
            """,
            transaction_id,
        )
    return {"transaction_id": transaction_id, "history": [dict(r) for r in rows]}


import httpx
