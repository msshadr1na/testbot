from infrastructure.repositories import (
    BookingRepository,
    UserRepository,
    SettingsRepository,
    OrganizationRepository,
    OrganizationMemberRepository,
    TrainingRepository,
    InviteRepository,
    GymRepository,
    ReviewRepository,
)
from app.models import Settings, User, Organization, OrganizationMember, Booking, Review
import calendar
from datetime import date

class UserService:
    def __init__(self, user_repository : UserRepository, settings_repository: SettingsRepository):
        self.user_repository = user_repository
        self.settings_repository = settings_repository

    async def find_by_tgid(self, telegram_id):
        return await self.user_repository.find(telegram_id)

    async def get_by_id(self, user_id):
        return await self.user_repository.get_by_id(user_id)

    async def registration(self, telegram_id, phone, first_name, last_name, middle_name):
        default_settings = Settings(id=None, notification_settings={"before_hour": 0, "before_day": 1})
        saved_settings = await self.settings_repository.create(default_settings)
        newUser = User(None, telegram_id, phone, first_name, last_name, saved_settings.id, middle_name)
        return await self.user_repository.create(newUser)

    async def update(self, user: User):
        await self.user_repository.update(user)

    async def get_notification_settings(self, user_id: int) -> dict:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")
        settings = await self.settings_repository.get_by_id(user.settings_id)
        if not settings or settings.notification_settings is None:
            return {"before_hour": 0, "before_day": 1}
        raw = settings.notification_settings
        if isinstance(raw, str):
            import json
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
        else:
            data = dict(raw or {})
        return {
            "before_day": data.get("before_day", 1),
            "before_hour": data.get("before_hour", 0),
        }

    async def update_notification_settings(self, user_id: int, before_day, before_hour):
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")
        settings_data = {"before_hour": before_hour, "before_day": before_day}
        new_settings = Settings(id=None, notification_settings=settings_data)
        saved = await self.settings_repository.create(new_settings)
        user.settings_id = saved.id
        await self.user_repository.update(user)




class OrganizationService:
    def __init__(self, organization_repository : OrganizationRepository, 
                 organizationMember_repository : OrganizationMemberRepository, 
                 invite_repository: InviteRepository, gym_repository: GymRepository, 
                 training_repository: TrainingRepository):
        self.organization_repository = organization_repository
        self.organizationMember_repository = organizationMember_repository
        self.invite_repository = invite_repository
        self.gym_repository = gym_repository
        self.training_repository = training_repository

    async def get_schedule(self, user_id: int, org_id: int, start_date, end_date):
        return await self.organization_repository.get_client_schedule(user_id, org_id, start_date, end_date)


    async def get_schedule_for_calendar(self, org_id: int, year: int, month: int):
        """Возвращает словарь {дата: количество тренировок} для календаря"""

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        # Теперь вызываем новую функцию
        counts = await self.training_repository.get_trainings_counts_by_org_grouped_by_day(
            org_id, start_date, end_date)
        # Преобразуем в словарь
        by_day = {day: count for day, count in counts}
        return by_day

    async def get_schedule_for_worker(self, worker_id: int, days_ahead: int = 7):
        """Возвращает тренировки работника на N дней вперёд"""
        from datetime import datetime, timedelta
        now = datetime.now()
        future = now + timedelta(days=days_ahead)
        rows = await self.training_repository.get_trainings_by_trainer_in_period(worker_id, now, future)
        return rows
# Поиск организации по названию
    async def find_by_name(self, name):
        return await self.organization_repository.find_by_name(name)

    async def get_by_id(self,id):
        organization = await self.organization_repository.find_by_id(id)
        return organization
# Редактирование названия организации
    async def update_name(self, org_id, new_name):
        organization = await self.organization_repository.find_by_id(org_id)
        organization.name = new_name
        updated_organization = await self.organization_repository.update(organization)
        return updated_organization

# Создание организации (добавление в бд)
    async def create_organization(self, user: User, name):
        newOrganization = Organization(None,name)
        savedOrganization = await self.organization_repository.create(newOrganization)
        newOrganizationMember = OrganizationMember(None,user.id,1,savedOrganization.id)
        owner = await self.organizationMember_repository.create(newOrganizationMember)
        return savedOrganization

# Удаление организации и всех зависимостей
    async def delete_organization(self, user_id, org_id):      
        organization = await self.organization_repository.find_by_id(org_id)
        if not organization:
            raise ValueError("Организация не найдена")

        organization = await self.organization_repository.delete(org_id)
        return organization

# Просмотр организаций, которыми пользователь владеет
    async def show_owned_orgs(self, user_id):
        # Получаем только ID организаций, где пользователь — владелец (role_id = 1)
        org_ids = await self.organizationMember_repository.get_membered_orgs(user_id, 1)

        if not org_ids:
            return [], []

        # Теперь получаем названия напрямую по ID
        names = await self.organization_repository.get_names_by_ids(org_ids)

        return org_ids, names

#Создание ссылки-приглашения для организации
    async def create_invite(self, organization_id, role_id):
        invite = await self.invite_repository.create(organization_id, role_id)
        bot_username = "devmmmBot"
        return f"https://t.me/{bot_username}?start=join_{invite.code}"

#Принятие приглашения
    async def accept_invite(self, code, user_id):
        invite = await self.invite_repository.get_by_code(code)
        if not invite:
            raise ValueError("Приглашение не найдено")

        existing = await self.organizationMember_repository.get_by_user_and_org_any_role(user_id, invite.organization_id)
        if existing:
            raise ValueError("Вы уже состоите в этой организации")

        member = OrganizationMember(None, user_id, invite.role_id, invite.organization_id)

        try:
            await self.organizationMember_repository.create(member)
        except Exception as e:
            if "organization_member_user_id_organization_id_key" in str(e):
                raise ValueError("Вы уже состоите в этой организации")
            raise

        return invite.role_id

    async def get_or_create_invite(self, organization_id: int, role_id: int) -> str:

        existing_invite = await self.invite_repository.get_by_org_and_role(organization_id, role_id)
        if existing_invite:
            bot_username = "devmmmBot"
            return f"https://t.me/{bot_username}?start=join_{existing_invite.code}"
    
        return await self.create_invite(organization_id, role_id)

    #Получение организации из кода приглашения
    async def get_org_id_from_invite(self, code):
        invite = await self.invite_repository.get_by_code(code)
        if not invite:
            raise ValueError("Приглашение не найдено")
        return invite.organization_id

    #Обновление ссылки-приглашения для организации и роли
    async def update_invite(self, organization_id, role_id):
        await self.invite_repository.delete_by_org_and_role(organization_id, role_id)
        return await self.create_invite(organization_id, role_id)

    #Получение всех работников организации
    async def get_workers_list(self, org_id):
        workers = await self.organizationMember_repository.get_members_by_org_and_role(org_id, 2)
        return workers

    #Удаление работника из организации
    async def delete_worker(self, org_id, user_id):
        worker = await self.organizationMember_repository.get_by_user_and_org(user_id, org_id, 2)
        await self.organizationMember_repository.delete(worker)
        return worker

    #Удаление клиента из организации
    async def delete_client(self, org_id, user_id):
        client = await self.organizationMember_repository.get_by_user_and_org(user_id, org_id, 3)
        await self.organizationMember_repository.delete(client)
        return client

    #Получение всех клиентов организации
    async def get_clients_list(self, org_id):
        clients = await self.organizationMember_repository.get_members_by_org_and_role(org_id, 3)
        return clients

    #Получение всех помещений организации
    async def get_places_list(self, org_id):
        gyms = await self.gym_repository.get_gyms_by_org_id(org_id)
        return gyms

    # Получение всех названий помещений организации
    async def get_places_names_list(self, org_id):
        gyms = await self.gym_repository.get_gyms_names_by_org_id(org_id)
        return gyms

    #Получение помещения по id
    async def get_place_by_id(self, place_id):
        gym = await self.gym_repository.find_by_id(place_id)
        return gym

    #Создание помещения
    async def create_place(self, org_id, name):
        gym = await self.gym_repository.create(name, org_id)
        return gym

    async def update_place_name(self, place_id: int, name: str):
        return await self.gym_repository.update_name(place_id, name)

    async def delete_place(self, place_id: int):
        return await self.gym_repository.delete_by_id(place_id)

    async def show_client_orgs(self, user_id):
        org_ids = await self.organizationMember_repository.get_membered_orgs(user_id, 3)

        if not org_ids:
            return [], []

        names = await self.organization_repository.get_names_by_ids(org_ids)

        return org_ids, names

    async def show_worker_orgs(self, user_id):
        org_ids = await self.organizationMember_repository.get_membered_orgs(user_id, 2)

        if not org_ids:
            return [], []

        names = await self.organization_repository.get_names_by_ids(org_ids)

        return org_ids, names

    async def get_membership_any_role(self, user_id: int, org_id: int):
        return await self.organizationMember_repository.get_by_user_and_org_any_role(user_id, org_id)

    async def list_org_ids_and_names_by_member_role(self, user_id: int, role_id: int):
        org_ids = await self.organizationMember_repository.get_membered_orgs(user_id, role_id)
        if not org_ids:
            return [], []
        names = await self.organization_repository.get_names_by_ids(org_ids)
        return org_ids, names

class TrainingTypeService:
    def __init__(self, training_repo: TrainingRepository):
        self.training_repo = training_repo

    async def get_type_name(self, type_id: int):
        t = await self.training_repo.get_training_type_by_id(type_id)
        return t.name


class TrainingService:
    def __init__(self, training_repository: TrainingRepository):
        self._training = training_repository

    async def get_trainings_by_trainer_and_org_in_period(self, trainer_id: int, org_id: int, start, end):
        return await self._training.get_trainings_by_trainer_and_org_in_period(trainer_id, org_id, start, end)

    async def get_trainings_counts_by_org_grouped_by_day(self, org_id: int, start_date, end_date):
        return await self._training.get_trainings_counts_by_org_grouped_by_day(org_id, start_date, end_date)

    async def get_trainings_with_details_by_org_and_date_range(self, org_id: int, start_date, end_date):
        return await self._training.get_trainings_with_details_by_org_and_date_range(org_id, start_date, end_date)

    async def get_training_types(self, org_id: int):
        return await self._training.get_training_types(org_id)

    async def has_gym_conflict(self, org_id: int, gym_id: int, date_start, date_end, exclude_training_id=None):
        return await self._training.has_gym_conflict(org_id, gym_id, date_start, date_end, exclude_training_id)

    async def has_trainer_conflict(self, trainer_id: int, date_start, date_end, exclude_training_id=None):
        return await self._training.has_trainer_conflict(trainer_id, date_start, date_end, exclude_training_id)

    async def create(self, training):
        return await self._training.create(training)

    async def find_training_type_by_name(self, name: str, org_id: int):
        return await self._training.find_training_type_by_name(name, org_id)

    async def create_training_type(self, name: str, org_id: int):
        return await self._training.create_training_type(name, org_id)

    async def get_by_id(self, training_id: int):
        return await self._training.get_by_id(training_id)

    async def update(self, training_id: int, gym_id: int, trainer_id: int, date_start, date_end, type_id: int, max_clients: int):
        return await self._training.update(training_id, gym_id, trainer_id, date_start, date_end, type_id, max_clients)

    async def delete_by_id(self, training_id: int):
        return await self._training.delete_by_id(training_id)

    async def count_past_trainings_for_trainer(self, org_id: int, trainer_id: int):
        return await self._training.count_past_trainings_for_trainer(org_id, trainer_id)

    async def get_past_trainings_for_trainer_page(self, org_id: int, trainer_id: int, limit: int, offset: int):
        return await self._training.get_past_trainings_for_trainer_page(org_id, trainer_id, limit, offset)

    async def exists_for_trainer(self, training_id: int, org_id: int, trainer_id: int):
        return await self._training.exists_for_trainer(training_id, org_id, trainer_id)

    async def exists_in_org(self, training_id: int, org_id: int):
        return await self._training.exists_in_org(training_id, org_id)


class BookingService:
    def __init__(self, booking_repository: BookingRepository):
        self._booking = booking_repository

    async def get_user_bookings_in_period(self, user_id: int, org_id: int, start, end):
        return await self._booking.get_user_bookings_in_period(user_id, org_id, start, end)

    async def get_user_telegram_ids_by_training_id(self, training_id: int):
        return await self._booking.get_user_telegram_ids_by_training_id(training_id)

    async def get_by_training_id(self, training_id: int):
        return await self._booking.get_by_training_id(training_id)

    async def delete_all_by_training_id(self, training_id: int):
        return await self._booking.delete_all_by_training_id(training_id)

    async def create(self, booking: Booking):
        return await self._booking.create(booking)

    async def get_training_booking_row(self, user_id: int, training_id: int, org_id: int):
        return await self._booking.get_training_booking_row(user_id, training_id, org_id)

    async def delete_booking_for_user_training(self, user_id: int, training_id: int):
        return await self._booking.delete_booking_for_user_training(user_id, training_id)

    async def count_past_bookings_for_user_in_org(self, user_id: int, org_id: int, now_dt):
        return await self._booking.count_past_bookings_for_user_in_org(user_id, org_id, now_dt)

    async def get_client_history_page(self, user_id: int, org_id: int, limit: int, offset: int, review_table_exists: bool, now_dt):
        if review_table_exists:
            return await self._booking.get_client_history_page_with_review(user_id, org_id, limit, offset, now_dt)
        return await self._booking.get_client_history_page_without_review(user_id, org_id, limit, offset, now_dt)

    async def user_has_completed_booking(self, user_id: int, org_id: int, training_id: int, now_dt):
        return await self._booking.user_has_completed_booking(user_id, org_id, training_id, now_dt)

    async def get_upcoming_with_settings(self, start_dt, end_dt):
        return await self._booking.get_upcoming_with_settings(start_dt, end_dt)


class ReviewService:
    def __init__(self, review_repository: ReviewRepository, booking_repository: BookingRepository, training_repository: TrainingRepository):
        self._review = review_repository
        self._booking = booking_repository
        self._training = training_repository

    async def table_exists(self) -> bool:
        return await self._review.table_exists()

    async def get_by_training_id(self, training_id: int):
        return await self._review.get_by_training_id(training_id)

    async def get_worker_training_stats(self, org_id: int, training_id: int, trainer_user_id: int):
        if not await self._training.exists_for_trainer(training_id, org_id, trainer_user_id):
            return None
        if not await self._review.table_exists():
            return {"avg_grade": None, "reviews": []}
        avg_grade = await self._review.get_avg_grade_for_training(training_id)
        reviews = await self._review.list_reviews_with_author_for_training(training_id)
        return {
            "avg_grade": avg_grade,
            "reviews": [{"grade": r["grade"], "text": r["text"] or "", "author": r["author"]} for r in reviews],
        }

    async def create_client_review(self, user_id: int, org_id: int, training_id: int, grade: int, text: str):
        if not await self._review.table_exists():
            raise ValueError("reviews_unavailable")
        from datetime import datetime
        if not await self._booking.user_has_completed_booking(user_id, org_id, training_id, datetime.now()):
            raise ValueError("training_not_found")
        existing = await self._review.find_id_by_user_and_training(user_id, training_id)
        if existing:
            raise ValueError("review_exists")
        review = Review(None, (text or "").strip(), grade, user_id, training_id)
        await self._review.create(review)




