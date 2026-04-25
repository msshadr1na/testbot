from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.factory import create_organization_service, create_user_service
from app.webapp.deps import get_db
from asyncpg import Pool
from app.models import Training
from infrastructure.repositories import BookingRepository, OrganizationMemberRepository, TrainingRepository
from app.webapp.schemas import UserName

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


def _validate_org_name(name: str):
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Organization name is too short")


def _validate_place_name(name: str):
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Place name is too short")


@router.get("/get-user", response_model=UserName)
async def get_user(telegram_id, db: Pool = Depends(get_db)):
    user_service = create_user_service(db)
    user_db = await user_service.find_by_tgid(telegram_id)

    if not user_db:
        return {"first_name": "Гость", "last_name": None}

    return UserName(first_name=user_db.first_name, last_name=user_db.last_name)


@router.get("/org/organizations")
async def get_user_organizations(user_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        return {"organizations": []}

    org_ids, names = await org_service.show_owned_orgs(user.id)
    organizations = [{"id": org_id, "name": name} for org_id, name in zip(org_ids, names)]
    return {"organizations": organizations}


@router.get("/me/organizations")
async def get_my_organizations_by_role(user_id: int, role_id: int, db: Pool = Depends(get_db)):
    if role_id not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid role_id")
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        return {"organizations": []}

    member_repo = OrganizationMemberRepository(db)
    org_service = create_organization_service(db)
    org_ids = await member_repo.get_membered_orgs(user.id, role_id)
    names = await org_service.organization_repository.get_names_by_ids(org_ids)
    organizations = [{"id": org_id, "name": name} for org_id, name in zip(org_ids, names)]
    return {"organizations": organizations}


@router.post("/org")
async def create_organization(name: str, first_place_name: str, user_id: int, db: Pool = Depends(get_db)):
    _validate_org_name(name)
    _validate_place_name(first_place_name)
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    org_service = create_organization_service(db)
    existing = await org_service.find_by_name(name.strip())
    if existing:
        raise HTTPException(status_code=400, detail="Organization name already exists")

    org = await org_service.create_organization(user, name.strip())
    await org_service.create_place(org.id, first_place_name.strip())
    return {"id": org.id, "name": org.name}


@router.get("/org/{org_id}")
async def get_organization(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    org = await org_service.get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"id": org.id, "name": org.name}


@router.put("/org/{org_id}")
async def update_organization_name(org_id: int, name: str, db: Pool = Depends(get_db)):
    _validate_org_name(name)
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


@router.get("/org/{org_id}/workers/{worker_id}/schedule")
async def get_worker_schedule(org_id: int, worker_id: int, days: int = 3, db: Pool = Depends(get_db)):
    training_repo = TrainingRepository(db)
    now = datetime.now()
    horizon = now + timedelta(days=max(1, min(days, 14)))
    rows = await training_repo.get_trainings_by_trainer_and_org_in_period(worker_id, org_id, now, horizon)
    return {
        "schedule": [
            {
                "training_id": row["id"],
                "date_start": row["date_start"].isoformat(),
                "date_end": row["date_end"].isoformat(),
                "gym_name": row["gym_name"],
                "type_name": row["type_name"],
            }
            for row in rows
        ]
    }


@router.delete("/org/{org_id}/workers/{worker_id}")
async def delete_worker(org_id: int, worker_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    await org_service.delete_worker(org_id, worker_id)
    return {"ok": True}


@router.get("/org/{org_id}/clients")
async def get_clients(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    clients = await org_service.get_clients_list(org_id)
    return {"clients": [{"id": client_id, "name": name} for client_id, name in clients]}


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


@router.get("/org/{org_id}/places")
async def get_places(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    places = await org_service.get_places_list(org_id)
    return {"places": [{"id": place_id, "name": name} for place_id, name in places]}


@router.get("/org/{org_id}/places/{place_id}")
async def get_place(org_id: int, place_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    place = await org_service.get_place_by_id(place_id)
    if place is None or place.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Place not found")
    return {"id": place.id, "name": place.name, "organization_id": place.organization_id}


@router.put("/org/{org_id}/places/{place_id}")
async def update_place(org_id: int, place_id: int, name: str, db: Pool = Depends(get_db)):
    _validate_place_name(name)
    org_service = create_organization_service(db)
    place = await org_service.get_place_by_id(place_id)
    if place is None or place.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Place not found")
    updated = await org_service.update_place_name(place_id, name.strip())
    return {"id": updated.id, "name": updated.name, "organization_id": updated.organization_id}


@router.delete("/org/{org_id}/places/{place_id}")
async def delete_place(org_id: int, place_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    place = await org_service.get_place_by_id(place_id)
    if place is None or place.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Place not found")
    await org_service.delete_place(place_id)
    return {"ok": True}


@router.get("/org/{org_id}/events/calendar")
async def get_events_calendar(org_id: int, year: int, month: int, db: Pool = Depends(get_db)):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    training_repo = TrainingRepository(db)
    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    by_day = await training_repo.get_trainings_counts_by_org_grouped_by_day(
        org_id, start_date, end_date
    )
    return {
        "year": year,
        "month": month,
        "days": [{"date": d.isoformat(), "count": c} for d, c in by_day],
    }


@router.get("/org/{org_id}/events/day")
async def get_events_day(org_id: int, day: str, db: Pool = Depends(get_db)):
    try:
        day_date = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid day format")
    training_repo = TrainingRepository(db)
    rows = await training_repo.get_trainings_by_org_and_date_range(org_id, day_date, day_date + timedelta(days=1))
    return {
        "trainings": [
            {
                "id": row.id,
                "date_start": row.date_start.isoformat(),
                "date_end": row.date_end.isoformat(),
                "gym_id": row.gym_id,
                "trainer_id": row.trainer_id,
                "type_id": row.type_id,
                "max_clients": row.max_clients,
            }
            for row in rows
        ]
    }


@router.get("/org/{org_id}/events/options")
async def get_event_options(org_id: int, db: Pool = Depends(get_db)):
    org_service = create_organization_service(db)
    training_repo = TrainingRepository(db)

    places = await org_service.get_places_list(org_id)
    workers = await org_service.get_workers_list(org_id)
    types = await training_repo.get_training_types()
    return {
        "places": [{"id": place_id, "name": name} for place_id, name in places],
        "workers": [{"id": worker_id, "name": name} for worker_id, name in workers],
        "types": [{"id": type_id, "name": name} for type_id, name in types],
    }


@router.post("/org/{org_id}/events")
async def create_event(
    org_id: int,
    day: str,
    time_start: str,
    time_end: str,
    gym_id: int,
    trainer_id: int,
    type_id: int,
    max_clients: int,
    db: Pool = Depends(get_db),
):
    if max_clients < 1:
        raise HTTPException(status_code=400, detail="max_clients must be > 0")
    try:
        date_start = datetime.strptime(f"{day} {time_start}", "%Y-%m-%d %H:%M")
        date_end = datetime.strptime(f"{day} {time_end}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")
    if date_end <= date_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    training_repo = TrainingRepository(db)
    training = Training(
        id=None,
        organization_id=org_id,
        gym_id=gym_id,
        trainer_id=trainer_id,
        date_start=date_start,
        date_end=date_end,
        type_id=type_id,
        max_clients=max_clients,
    )
    created = await training_repo.create(training)
    return {
        "id": created.id,
        "organization_id": created.organization_id,
    }


@router.get("/worker/{org_id}/schedule")
async def get_my_worker_schedule(org_id: int, user_id: int, days: int = 3, db: Pool = Depends(get_db)):
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    training_repo = TrainingRepository(db)
    now = datetime.now()
    horizon = now + timedelta(days=max(1, min(days, 14)))
    rows = await training_repo.get_trainings_by_trainer_and_org_in_period(user.id, org_id, now, horizon)
    return {
        "schedule": [
            {
                "training_id": row["id"],
                "date_start": row["date_start"].isoformat(),
                "date_end": row["date_end"].isoformat(),
                "gym_name": row["gym_name"],
                "type_name": row["type_name"],
            }
            for row in rows
        ]
    }


@router.get("/client/{org_id}/bookings")
async def get_my_client_bookings(org_id: int, user_id: int, days: int = 30, db: Pool = Depends(get_db)):
    user = await _resolve_user_by_any_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    booking_repo = BookingRepository(db)
    now = datetime.now()
    horizon = now + timedelta(days=max(1, min(days, 60)))
    rows = await booking_repo.get_user_bookings_in_period(user.id, org_id, now, horizon)
    return {
        "bookings": [
            {
                "booking_id": row["booking_id"],
                "training_id": row["training_id"],
                "date_start": row["date_start"].isoformat(),
                "date_end": row["date_end"].isoformat(),
                "gym_name": row["gym_name"],
                "type_name": row["type_name"],
            }
            for row in rows
        ]
    }

