"""Health check endpoints."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/health", summary="Service health check")
async def health():
    return {"status": "healthy", "service": "cora-api-gateway", "version": "1.0.0"}

@router.get("/", include_in_schema=False)
async def root():
    return {"message": "CORA - Compliance Oriented Regulatory Assistant"}
