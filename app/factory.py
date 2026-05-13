# app/factory.py
from infrastructure.repositories import (
    OrganizationRepository,
    OrganizationMemberRepository,
    InviteRepository,
    GymRepository,
    TrainingRepository,
    UserRepository,
    SettingsRepository,
    BookingRepository,
    ReviewRepository,
)
from app.services import (
    OrganizationService,
    UserService,
    TrainingService,
    BookingService,
    ReviewService,
    TrainingTypeService,
)


def create_organization_service(pool):
    return OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )


def create_user_service(pool):
    return UserService(UserRepository(pool), SettingsRepository(pool))


def create_training_service(pool):
    return TrainingService(TrainingRepository(pool))


def create_booking_service(pool):
    return BookingService(BookingRepository(pool))


def create_review_service(pool):
    return ReviewService(
        ReviewRepository(pool),
        BookingRepository(pool),
        TrainingRepository(pool),
    )


def create_training_type_service(pool):
    return TrainingTypeService(TrainingRepository(pool))