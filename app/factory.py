# app/factory.py
from infrastructure.repositories import (
    OrganizationRepository, OrganizationMemberRepository,
    InviteRepository, GymRepository, TrainingRepository, UserRepository
)
from app.services import OrganizationService

def create_organization_service(pool):
    return OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool)
    )

def create_user_service(pool):
    return UserService(UserRepository(pool), SettingsRepository(pool))