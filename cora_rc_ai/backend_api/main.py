"""
CORA FastAPI Backend - Main entry point.
Provides REST API for transaction screening, regulatory queries, reports, and audit logs.
Connects to the Agentic backend via internal HTTP calls.
"""
import os
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cora_rc_ai.backend_api.api.v1 import transactions, regulations, reports, audit, health, chats
from cora_rc_ai.backend_api.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CORA FastAPI backend starting...")
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.AGENTIC_BACKEND_URL,
        timeout=120.0,
    )
    yield
    await app.state.http_client.aclose()
    logger.info("CORA FastAPI backend shut down.")


app = FastAPI(
    title="CORA API Gateway",
    description="AI-powered Compliance Oriented Regulatory Assistant - REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(regulations.router, prefix="/api/v1/regulations", tags=["Regulations"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["Chats"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cora_rc_ai.backend_api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1,
    )
