from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    first_name = State()
    last_name = State()
    middle_name = State()
    phone = State()

class CreatingOrganizationState(StatesGroup):
    name = State()
    place_name = State()

class UserState(StatesGroup):
    role = State()
    organization = State()
    editing_org_name = State()
    creating_place = State()
    menu = State()