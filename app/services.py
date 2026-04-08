from infrastructure.repositories import BookingRepository, UserRepository, SettingsRepository, OrganizationRepository, OrganizationMemberRepository, TrainingRepository, InviteRepository
from app.models import Settings, User, Organization, OrganizationMember
from presentation.handlers import delete_worker

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
    def __init__(self, organization_repository : OrganizationRepository, organizationMember_repository : OrganizationMemberRepository, invite_repository: InviteRepository):
        self.organization_repository = organization_repository
        self.organizationMember_repository = organizationMember_repository
        self.invite_repository = invite_repository

# Поиск организации по названию
    async def find_by_name(self, name):
        return await self.organization_repository.find_by_name(name)

    async def get_by_id(self,id):
        organization = await self.organization_repository.find_by_id(id)
        return organization

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
    async def show_owned_orgs(self,user_id):
        org_ids = await self.organizationMember_repository.get_membered_orgs(user_id, 1)
        names = await self.organizationMember_repository.get_names_by_ids(org_ids)
        return org_ids, names

# Редактирование созданной организации


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

        existing = await self.organizationMember_repository.get_by_user_and_org(user_id, invite.organization_id)
        if existing:
            raise ValueError("Вы уже состоите в этой организации")

        member = OrganizationMember(None, user_id, invite.role_id, invite.organization_id)

        await self.organizationMember_repository.create(member)

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

    async def delete_worker(self, org_id, user_id):
        worker = await self.organizationMember_repository.get_by_user_and_org(user_id, org_id, 2)
        await self.organizationMember_repository.delete(worker)
        return worker




