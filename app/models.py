
class Settings:
    def __init__(self, id, notification_settings):
        self.id = id
        self.notification_settings = notification_settings

class User:
    def __init__(self, id, telegram_id, phone, first_name, last_name, settings_id, middle_name = None):
        self.id = id
        self.telegram_id = telegram_id
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.settings_id = settings_id

class Role:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class Organization:
    def __init__(self,id, name):
        self.id = id
        self.name = name

class Gym:
    def __init__(self,id,name,organization_id):
        self.id = id
        self.name = name
        self.organization_id = organization_id

class OrganizationMember:
    def __init__(self,id,user_id, role_id, organization_id):
        self.id = id
        self.user_id = user_id
        self.role_id = role_id
        self.organization_id = organization_id

class TrainingType:
    def __init__(self,id,name):
        self.id = id
        self.name = name

class Training:
    def __init__(self,id, organization_id, gym_id, trainer_id, date_start, date_end, type_id,
                 max_clients):
        self.id = id
        self.organization_id = organization_id
        self.gym_id = gym_id
        self.trainer_id = trainer_id
        self.date_start = date_start
        self.date_end = date_end
        self.type_id = type_id
        self.max_clients = max_clients

class Booking:
    def __init__(self,id,user_id,training_id,created_at):
        self.id = id
        self.user_id = user_id
        self.training_id = training_id
        self.created_at = created_at

class Review:
    def __init__(self, id, text, grade, user_id, training_id):
        self.id = id
        self.text = text
        self.grade = grade
        self.user_id = user_id
        self.training_id = training_id

class Invite:
    def __init__(self, id, organization_id, role_id, code):
        self.id = id
        self.organization_id = organization_id
        self.role_id = role_id
        self.code = code

