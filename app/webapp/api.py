from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from app.factory import create_organization_service, create_user_service
from app.webapp.deps import get_db
from asyncpg import Pool
from app.models import Training
from infrastructure.repositories import BookingRepository, OrganizationMemberRepository, TrainingRepository
from app.webapp.schemas import UserName
from config import bot_token
import json
from urllib.request import Request, urlopen

router = APIRouter(prefix="/api/v1", tags=["Web App"])


async def _send_telegram_message(telegram_id: int, text: str):
    if not telegram_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": telegram_id, "text": text}).encode("utf-8")

    def _post():
        req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=5):
            return

    try:
        import asyncio
        await asyncio.to_thread(_post)
    except Exception:
        return


async def _broadcast_telegram_messages(telegram_ids: list[int], text: str):
    unique_ids = {tg_id for tg_id in telegram_ids if tg_id}
    for tg_id in unique_ids:
        await _send_telegram_message(tg_id, text)

@router.get("/health")
async def health():
    return {"status": "ok"}

async def _resolve_user_by_any_id(user_id: int, db: Pool):
    user_service = create_user_service(db)
    user = await user_service.find_by_tgid(user_id)
    if user is None:
        user = await user_service.get_by_id(user_id)
    return user


def _validate_place_name(name: str):
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Place name is too short")


@router.get("/get-user", response_model=UserName)
async def get_user(telegram_id: int = Query(...), db: Pool = Depends(get_db)):
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

@router.post("/org")
async def create_organization(name: str, first_place_name: str, user_id: int, db: Pool = Depends(get_db)):
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
    org_service = create_organization_service(db)
    existing = await org_service.get_by_id(org_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    existing = await org_service.find_by_name(name.strip())
    if existing:
        raise HTTPException(status_code=409, detail="Organization name already exists")
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
    user_service = create_user_service(db)
    worker = await user_service.get_by_id(worker_id)
    org = await org_service.get_by_id(org_id)
    await org_service.delete_worker(org_id, worker_id)
    if worker and org:
        await _send_telegram_message(worker.telegram_id, f"Вы были удалены из организации {org.name}.")
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
    user_service = create_user_service(db)
    client = await user_service.get_by_id(client_id)
    org = await org_service.get_by_id(org_id)
    await org_service.delete_client(org_id, client_id)
    if client and org:
        await _send_telegram_message(client.telegram_id, f"Вы были удалены из организации {org.name}.")
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
    places = await org_service.get_places_list(org_id)
    if len(places) <= 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить единственное помещение организации")
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
    rows = await training_repo.get_trainings_with_details_by_org_and_date_range(org_id, day_date, day_date + timedelta(days=1))
    return {
        "trainings": [
            {
                "id": row["id"],
                "date_start": row["date_start"].isoformat(),
                "date_end": row["date_end"].isoformat(),
                "gym_id": row["gym_id"],
                "trainer_id": row["trainer_id"],
                "type_id": row["type_id"],
                "max_clients": row["max_clients"],
                "trainer_name": row["trainer_name"],
                "gym_name": row["gym_name"],
                "type_name": row["type_name"],
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


@router.post("/org/{org_id}/events/types")
async def create_event_type(org_id: int, name: str, db: Pool = Depends(get_db)):
    type_name = (name or "").strip()
    if len(type_name) < 2:
        raise HTTPException(status_code=400, detail="Название типа слишком короткое")
    training_repo = TrainingRepository(db)
    existing = await training_repo.find_training_type_by_name(type_name)
    if existing:
        return {"id": existing["id"], "name": existing["name"]}
    created = await training_repo.create_training_type(type_name)
    return {"id": created["id"], "name": created["name"]}


@router.get("/org/{org_id}/events/{training_id}")
async def get_event_detail(org_id: int, training_id: int, db: Pool = Depends(get_db)):
    training_repo = TrainingRepository(db)
    training = await training_repo.get_by_id(training_id)
    if not training or training.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Training not found")
    return {
        "id": training.id,
        "organization_id": training.organization_id,
        "gym_id": training.gym_id,
        "trainer_id": training.trainer_id,
        "type_id": training.type_id,
        "max_clients": training.max_clients,
        "date_start": training.date_start.isoformat(),
        "date_end": training.date_end.isoformat(),
    }


@router.put("/org/{org_id}/events/{training_id}")
async def update_event(
    org_id: int,
    training_id: int,
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
    existing = await training_repo.get_by_id(training_id)
    if not existing or existing.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Training not found")

    updated = await training_repo.update(training_id, gym_id, trainer_id, date_start, date_end, type_id, max_clients)
    return {"id": updated.id, "organization_id": updated.organization_id}


@router.delete("/org/{org_id}/events/{training_id}")
async def delete_event(org_id: int, training_id: int, db: Pool = Depends(get_db)):
    training_repo = TrainingRepository(db)
    booking_repo = BookingRepository(db)
    user_service = create_user_service(db)
    org_service = create_organization_service(db)

    training = await training_repo.get_by_id(training_id)
    if not training or training.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Training not found")

    org = await org_service.get_by_id(org_id)
    user_ids = await booking_repo.get_user_ids_by_training_id(training_id)
    trainer = await user_service.get_by_id(training.trainer_id)
    users_to_notify = []
    if trainer:
        users_to_notify.append(trainer.telegram_id)
    for uid in user_ids:
        user = await user_service.get_by_id(uid)
        if user:
            users_to_notify.append(user.telegram_id)

    await booking_repo.delete_all_by_training_id(training_id)
    await training_repo.delete_by_id(training_id)

    org_name = org.name if org else "организации"
    await _broadcast_telegram_messages(
        users_to_notify,
        f"Тренировка в организации {org_name} была отменена.",
    )
    return {"ok": True}


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

