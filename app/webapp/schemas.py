from pydantic import BaseModel
from typing import List

class UserName(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

class TrainingResponse(BaseModel):
    id: int
    time: str
    duration: int
    place: str
    type: str
    trainer: str
    available_spots: int
    total_spots: int
    is_booked: bool

class ScheduleResponse(BaseModel):
    trainings: List[TrainingResponse]