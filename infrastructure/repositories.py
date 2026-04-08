from multiprocessing import Pool
from app.models import Settings, TrainingType, Training, User, OrganizationMember, Organization, Gym, Booking, Review,Invite
import json
import secrets

class SettingsRepository:
    def __init__(self, pool):
        self.pool = pool

    async def create(self, settings: Settings):
        json_value = json.dumps(settings.notification_settings)
        sql_find = "select id from settings where notification_settings = $1"
        row = await self.pool.fetchrow(sql_find, json_value)
        if row:
            return Settings(id=row["id"], notification_settings=json_value)

        sql_insert = "insert into settings (notification_settings) values ($1) returning id"
        row = await self.pool.fetchrow(sql_insert, json_value)
        return Settings(id=row["id"], notification_settings=json_value)

class UserRepository:
    def __init__(self, pool):
        self.pool = pool

    async def create(self, user: User):
        sql = """insert into users (telegram_id, phone, first_name, last_name, middle_name, settings_id) values 
        ($1, $2, $3, $4, $5, $6) returning id"""
        row = await self.pool.fetchrow(sql, user.telegram_id, user.phone, user.first_name, user.last_name, user.middle_name, user.settings_id)
        user.id = row["id"]
        return user

    async def get_by_id(self, user_id: int):
        sql = "select * from users where id = $1"
        row = await self.pool.fetchrow(sql,user_id)

        if not row:
            return None
        else:
            user = User(row["id"], row["telegram_id"], row["phone"], row["first_name"], row["last_name"], row["settings_id"], row["middle_name"])
            return user

    async def find(self, telegram_id):
        sql = "select * from users where telegram_id = $1"
        row = await self.pool.fetchrow(sql,telegram_id)

        if not row:
            return None
        else:            
            user = User(row["id"], row["telegram_id"], row["phone"], row["first_name"], row["last_name"], row["middle_name"], row["settings_id"])
            return user

    async def update(self,user):
        sql = "update users set phone = $2, first_name = $3, last_name = $4, middle_name = $5, settings_id = $6 where id = $1"

        await self.pool.execute(sql, user.id, user.phone, user.first_name, user.last_name, user.middle_name, user.settings_id)

class OrganizationMemberRepository:
    def __init__(self,pool):
        self.pool = pool

    #Создание связи участника с организацией (добавление участника в организацию)
    async def create(self,member: OrganizationMember):
        sql = "insert into organization_member (user_id, role_id, organization_id) values ($1, $2, $3) returning id"
        row = await self.pool.fetchrow(sql, member.user_id, member.role_id, member.organization_id)

        member.id = row["id"]
        return member
    
    #Получение связи участника с организацией по id участника и id организации
    async def get_by_user_and_org(self, user_id, org_id):
        sql = "select * from organization_member where user_id = $1 and organization_id = $2"

        row = await self.pool.fetchrow(sql, user_id, org_id)
        return OrganizationMember(row["id"], row["user_id"], row["role_id"], row["organization_id"]) if row else None

    #Удаление связи участника с организацией
    async def delete(self, organization_member: OrganizationMember):
        sql = """delete from organization_member 
               where id = $1"""
        row = await self.pool.fetchrow(sql,organization_member.id)
        return

    #Удаление всех связей участника с организацией (при удалении организации)
    async def delete_all_by_org_id(self,org_id):
        sql = "delete from organization_member where organization_id = $1"
        deleted = await self.pool.execute(sql,org_id)

        return deleted
    #Получение всех организаций, в которых пользователь является участником с определенной ролью
    async def get_membered_orgs(self, user_id, role_id):
        sql = """select organization_member.organization_id from organization_member
                 inner join organization on organization_member.organization_id = organization.id
                 where user_id = $1 and role_id = $2"""
        org_ids = await self.pool.fetch(sql,user_id, role_id)

        return [org["organization_id"] for org in org_ids]

    #Получение названий организаций по их id
    async def get_names_by_ids(self, org_ids):
        sql = """select id, name from organization where id = any($1)"""
        rows = await self.pool.fetch(sql, org_ids)

        return [row["name"] for row in rows]

    #Получение всех участников организации с определенной ролью
    async def get_members_by_org_and_role(self, org_id, role_id):
        sql = """select om.user_id, concat_ws(' ',u.last_name,u.first_name,coalesce(u.middle_name,'')) as name
from organization_member om 
join users u on om.user_id = u.id
where organization_id = $1 and role_id = $2
order by name asc"""
        rows = await self.pool.fetch(sql, org_id, role_id)
        return [(row["user_id"], row["name"]) for row in rows]

class GymRepository:
    def __init__(self,pool):
        self.pool = pool

    async def create(self,gym: Gym):
        sql ="insert into gym (name, organization_id) values ($1, $2) returning id"
        row = await self.pool.fetchrow(sql, gym.name, gym.organization_id)

        gym.id = row["id"]
        return gym

    async def delete_all_by_org_id(self,org_id):
        sql = "delete from gym where organization_id = $1"
        deleted = await self.pool.execute(sql,org_id)

        return deleted

class OrganizationRepository:
    def __init__(self, pool):
        self.pool = pool

    async def create(self, organization: Organization):
        sql ="insert into organization (name) values ($1) returning id"
        row = await self.pool.fetchrow(sql, organization.name)

        organization.id = row["id"]
        return organization

    async def find_by_name(self, name):
        sql = "select * from organization where name = $1"
        row = await self.pool.fetchrow(sql,name)

        if not row:
            return None
        else:    
            return Organization(row["id"],row["name"])

    async def find_by_id(self, org_id):
        sql = "select * from organization where id = $1"
        row = await self.pool.fetchrow(sql,org_id)

        if not row:
            return None
        else:    
            return Organization(row["id"],row["name"])


    async def delete(self, org_id):
        sql = "delete from organization where id = $1"
        row = await self.pool.fetchrow(sql,org_id)
        return

class TrainingRepository:
    def __init__(self,pool):
        self.pool = pool
   
    async def create(self, training):
        sql = "insert into training (organization_id, gym_id, trainer_id, date_start, date_end, type_id, max_clients) values ($1, $2, $3, $4, $5, $6, $7) returning id"
        row = await self.pool.fetchrow(sql, training.organization_id, training.gym_id, training.trainer_id, training.date_start, training.date_end, training.type_id, training.max_clients)

        training.id = row["id"]
        return training

    async def get_by_org_id(self, org_id):
        sql = "select * from training where organization_id = $1"
        trainings = await self.pool.fetch(sql,org_id)

        return trainings

    async def delete_all_by_org_id(self,org_id):
        sql = "delete from training where organization_id = $1"
        deleted = await self.pool.execute(sql,org_id)

        return deleted

class BookingRepository:
    def __init__(self,pool):
        self.pool = pool

    async def create(self, booking:Booking):
        sql ="insert into booking (user_id, training_id, created_at) values ($1, $2, $3) returning id"
        row = await self.pool.fetchrow(sql, booking.user_id, booking.training_id, booking.created_at)

        booking.id = row["id"]
        return booking

    async def delete_all_by_training_id(self, training_id):
        sql = "delete from booking where training_id = $1"
        deleted = await self.pool.execute(sql, training_id)
        return deleted

class ReviewRepository:
    def __init__(self,pool):
        self.pool = pool

    async def create(self, review: Review):
        sql = "insert into review (user_id, training_id, grade, text) values ($1, $2, $3, $4) returning id"
        row = await self.pool.fetchrow(sql, review.user_id, review.training_id, review.grade, review.text)

        review.id = row["id"]
        return review

class InviteRepository:
    def __init__(self, pool):
        self.pool = pool
    # Создание ссылки-приглашения для организации и роли
    async def create(self, organization_id, role_id):
        code = secrets.token_urlsafe(12)
        sql ="""insert into invites (organization_id, role_id, code) values ($1, $2, $3)
            returning id, organization_id, role_id, code"""
        row = await self.pool.fetchrow(sql, organization_id, role_id, code)
        return Invite(**row)
    # Получение ссылки-приглашения по коду
    async def get_by_code(self, code):
        sql = """select id, organization_id, role_id, code from invites
            where code = $1"""
        row = await self.pool.fetchrow(sql, code)
        if row:
            return Invite(**row)
        return None
    # Получение ссылки-приглашения для организации и роли
    async def get_by_org_and_role(self, organization_id: int, role_id: int):
        sql = """select id, organization_id, role_id, code from invites
            where organization_id = $1 and role_id = $2"""
        row = await self.pool.fetchrow(sql, organization_id, role_id)
        if row:
            return Invite(**row)
        return None

    #Удаление ссылки-приглашения для организации и роли
    async def delete_by_org_and_role(self, organization_id: int, role_id: int):
        sql = """delete from invites where organization_id = $1 and role_id = $2"""
        await self.pool.execute(sql, organization_id, role_id)