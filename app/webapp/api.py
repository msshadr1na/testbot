from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.factory import create_organization_service, create_user_service
from app.webapp.deps import get_db
from asyncpg import Pool
from infrastructure.repositories import TrainingRepository

router = APIRouter(prefix="/api/v1", tags=["Web App"])

@router.get("/health")
async def health():
    return {"status": "ok"}

async def _resolve_user_by_any_id(user_id: int, db: Pool):
    user_service = create_user_service(db)
    user = await user_service.find_by_tgid(user_id)
    if user is None:
        user = await user_service.get_by_id(user_id)
    return user


@router.get("/org/organizations")
async def get_user_organizations(user_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        return {"organizations": []}

    org_ids, names = await org_service.show_owned_orgs(user.id)
    organizations = [{"id": org_id, "name": name} for org_id, name in zip(org_ids, names)]
    return {"organizations": organizations}


@router.get("/org/{org_id}")
async def get_organization(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    org = await org_service.get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"id": org.id, "name": org.name}


@router.put("/org/{org_id}")
async def update_organization_name(org_id: int, name: str, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    existing = await org_service.get_by_id(org_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    updated = await org_service.update_name(org_id, name.strip())
    return {"id": updated.id, "name": updated.name}


@router.delete("/org/{org_id}")
async def delete_organization(org_id: int, user_id: int, db: Pool = Depends(get_db)):
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    org_service = create_organization_service(db)
    await org_service.delete_organization(user.id, org_id)
    return {"ok": True}


@router.get("/org/{org_id}/workers")
async def get_workers(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    workers = await org_service.get_workers_list(org_id)
    return {"workers": [{"id": worker_id, "name": name} for worker_id, name in workers]}


@router.get("/org/{org_id}/workers/{worker_id}")
async def get_worker(org_id: int, worker_id: int, db: Pool = Depends(get_db)):
    user_service = create_user_service(db)
    worker = await user_service.get_by_id(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    full_name = f"{worker.last_name} {worker.first_name}".strip()
    if worker.middle_name:
        full_name = f"{full_name} {worker.middle_name}"
    return {
        "id": worker.id,
        "organization_id": org_id,
        "full_name": full_name,
        "phone": worker.phone,
    }


@router.delete("/org/{org_id}/workers/{worker_id}")
async def delete_worker(org_id: int, worker_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    await org_service.delete_worker(org_id, worker_id)
    return {"ok": True}


@router.get("/org/{org_id}/workers/invite")
async def get_workers_invite(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    link = await org_service.get_or_create_invite(org_id, 2)
    return {"link": link}


@router.post("/org/{org_id}/workers/invite/refresh")
async def refresh_workers_invite(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    link = await org_service.update_invite(org_id, 2)
    return {"link": link}


@router.get("/org/{org_id}/clients")
async def get_clients(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    clients = await org_service.get_clients_list(org_id)
    return {"clients": [{"id": client_id, "name": name} for client_id, name in clients]}


@router.get("/org/{org_id}/clients/{client_id}")
async def get_client(org_id: int, client_id: int, db: Pool = Depends(get_db)):
    user_service = create_user_service(db)
    client = await user_service.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    full_name = f"{client.last_name} {client.first_name}".strip()
    if client.middle_name:
        full_name = f"{full_name} {client.middle_name}"
    return {
        "id": client.id,
        "organization_id": org_id,
        "full_name": full_name,
        "phone": client.phone,
    }


@router.delete("/org/{org_id}/clients/{client_id}")
async def delete_client(org_id: int, client_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    await org_service.delete_client(org_id, client_id)
    return {"ok": True}


@router.get("/org/{org_id}/clients/invite")
async def get_clients_invite(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    link = await org_service.get_or_create_invite(org_id, 3)
    return {"link": link}


@router.post("/org/{org_id}/clients/invite/refresh")
async def refresh_clients_invite(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    link = await org_service.update_invite(org_id, 3)
    return {"link": link}


@router.get("/org/{org_id}/places")
async def get_places(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    places = await org_service.get_places_list(org_id)
    return {"places": [{"id": place_id, "name": name} for place_id, name in places]}


@router.get("/org/{org_id}/events/summary")
async def get_events_summary(org_id: int, db: Pool = Depends(get_db)):
    training_repo = TrainingRepository(db)
    today = date.today()
    upcoming_rows = await training_repo.get_trainings_by_org_and_date_range(
        org_id, today, today + timedelta(days=30)
    )
    by_day = await training_repo.get_trainings_counts_by_org_grouped_by_day(
        org_id, today, today + timedelta(days=30)
    )
    return {
        "upcoming_count": len(upcoming_rows),
        "days_with_trainings": len(by_day),
        "days": [{"date": d.isoformat(), "count": c} for d, c in by_day],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }