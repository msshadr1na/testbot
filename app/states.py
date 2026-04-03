from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    first_name = State()
    last_name = State()
    middle_name = State()
    phone = State()

class UserState(StatesGroup):
    role = State()
    organization = State()
    menu = State()