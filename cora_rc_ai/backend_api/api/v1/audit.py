"""
Audit trail endpoints.
Immutable, timestamped records of all compliance decisions and agent reasoning traces.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from cora_rc_ai.backend_api.core.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/trail", summary="Query audit trail with filters")
async def get_audit_trail(
    entity_type: Optional[str] = Query(None, description="transaction | regulation_query | report"),
    entity_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    risk_rating: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0),
):
    """
    Retrieve audit trail records with optional filters.
    All records are immutable once written.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        filters = ["1=1"]
        params = []
        idx = 1

        if entity_type:
            filters.append(f"entity_type = ${idx}")
            params.append(entity_type)
            idx += 1
        if entity_id:
            filters.append(f"entity_id = ${idx}")
            params.append(entity_id)
            idx += 1
        if from_date:
            filters.append(f"created_at >= ${idx}::timestamp")
            params.append(from_date)
            idx += 1
        if to_date:
            filters.append(f"created_at <= ${idx}::timestamp")
            params.append(to_date)
            idx += 1
        if risk_rating:
            filters.append(f"metadata->>'risk_rating' = ${idx}")
            params.append(risk_rating)
            idx += 1

        params.extend([limit, offset])
        query = f"""
            SELECT id, entity_type, entity_id, action, actor,
                   metadata, created_at
            FROM audit_logs
            WHERE {' AND '.join(filters)}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx+1}
        """
        rows = await conn.fetch(query, *params)

    return {
        "records": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/{audit_id}", summary="Get specific audit record")
async def get_audit_record(audit_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM audit_logs WHERE id = $1",
            audit_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return dict(row)


@router.get("/summary/risk-distribution", summary="Risk rating distribution summary")
async def risk_distribution(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    """Aggregated risk rating counts for dashboard display."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT risk_rating, COUNT(*) as count
            FROM transaction_screenings
            WHERE ($1::timestamp IS NULL OR screened_at >= $1::timestamp)
              AND ($2::timestamp IS NULL OR screened_at <= $2::timestamp)
            GROUP BY risk_rating
            ORDER BY count DESC
            """,
            from_date,
            to_date,
        )
    return {
        "distribution": [dict(r) for r in rows],
        "from_date": from_date,
        "to_date": to_date,
    }
