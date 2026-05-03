from infrastructure.repositories import BookingRepository, UserRepository, SettingsRepository, OrganizationRepository, OrganizationMemberRepository, TrainingRepository, InviteRepository,GymRepository
from app.models import Settings, User, Organization, OrganizationMember
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


