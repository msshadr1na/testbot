from fastapi import APIRouter, Depends, HTTPException
from app.factory import create_organization_service
from app.webapp.deps import get_db
from asyncpg import Pool

router = APIRouter(prefix="/api/v1", tags=["Web App"])

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/org/{org_id}/schedule")
async def get_org_schedule(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    by_day = await org_service.get_schedule_for_calendar(org_id, 2026, 4)
    return {"schedule": by_day}