from venv import create
from fastapi import APIRouter, Depends, HTTPException
from app.factory import OrganizationMemberRepository, create_organization_service, create_user_service
from app.webapp.deps import get_db
from asyncpg import Pool

router = APIRouter(prefix="/api/v1", tags=["Web App"])

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/org/organizations")
async def get_user_organizations(user_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    user_service = create_user_service(db)

    # WebApp иногда передает Telegram ID, а иногда внутренний user.id.
    # Поддерживаем оба варианта, чтобы список организаций стабильно открывался.
    user = await user_service.find_by_tgid(user_id)
    if user is None:
        user = await user_service.get_by_id(user_id)

    if user is None:
        return {"organizations": []}

    org_ids,names = await org_service.show_owned_orgs(user.id)

    organizations = []
    for id, n in zip(org_ids, names):
        organizations.append({"id": id, "name": n})

    return {"organizations": organizations}