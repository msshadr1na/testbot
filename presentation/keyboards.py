from aiogram.types import inline_keyboard_button, keyboard_button, users_shared, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from app.models import User

def build_start_keyboard():
    buttons =[[InlineKeyboardButton(text="Организатор", callback_data="owner")],
              [InlineKeyboardButton(text="Работник", callback_data="worker")],
              [InlineKeyboardButton(text="Клиент", callback_data="client")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура при выборе роли Организатор
async def build_org_keyboard(orgs,names):
    buttons = []

    for org_id, name in zip(orgs, names):
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"choose_org_{org_id}")])
    
    buttons.append([InlineKeyboardButton(text="Создать организацию",callback_data="create_org")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="start")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура при выборе конкретной организации для управления
def build_choose_org_keyboard(orgs,names):
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"choose_org_{org_id}")] for org_id, name in zip(orgs,names)]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="owner")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для управления организацией
def build_manage_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Редактировать", callback_data=f"edit_org_{org_id}")],
               [InlineKeyboardButton(text="Работники", callback_data=f"mng_workers_{org_id}")],
               [InlineKeyboardButton(text="Клиенты", callback_data=f"mng_clients_{org_id}")],
               [InlineKeyboardButton(text="Мероприятия", callback_data=f"mng_events_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data="owner")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для управления работниками организации
def build_manage_workers_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Просмотреть работников", callback_data=f"list.workers_{org_id}")],
               [InlineKeyboardButton(text="Пригласить работников", callback_data=f"invite.worker_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для управления ссылкой-приглашением для работников организации
def build_invite_workers_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Обновить ссылку-приглашение", callback_data=f"upd.code2_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"mng_workers_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для подтверждения удаления организации
def build_confirm_delete_org(org_id):
    buttons = [[InlineKeyboardButton(text="Удалить", callback_data=f"confirm_del_{org_id}")],
               [InlineKeyboardButton(text="Отмена", callback_data=f"choose_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard = buttons)
    return keyboard

#Список работников организации
def build_list_workers_keyboard(workers_list, page, org_id):
    total_pages = (len(workers_list) + 4) // 5
    start = page * 5
    end = start + 5
    current = workers_list[start:end]

    buttons = []

    for id, name in current:
        buttons.append([InlineKeyboardButton(text=name,callback_data=f"worker_chosen_{id}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="<=", callback_data=f"wrk.page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="=>", callback_data=f"wrk.page_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"mng_workers_{org_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

#Управление конкретным работником организации
def build_manage_worker_keyboard(wrk_id):
    buttons = [[InlineKeyboardButton(text="Удалить", callback_data=f"del_worker_{wrk_id}")],
               [InlineKeyboardButton(text="Расписание работника", callback_data=f"wrk_schedule_{wrk_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"wrk.page_0")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Удаление работника из организации
def build_confirm_delete_worker(wrk_id):
    buttons = [[InlineKeyboardButton(text="Удалить", callback_data=f"wrk_confirm_del_{wrk_id}")],
               [InlineKeyboardButton(text="Отмена", callback_data=f"worker_chosen_{wrk_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard = buttons)
    return keyboard

#Клавиатура для управления организацией
def build_edit_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Редактировать название", callback_data=f"edit_name_org_{org_id}")],
               [InlineKeyboardButton(text="Удалить организацию", callback_data=f"del_org_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"edit_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для отмены редактирования названия организации
def build_edit_name_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Отмена", callback_data=f"edit_org_{org_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#Клавиатура для управления клиентами организации
def build_manage_clients_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Просмотреть клиентов", callback_data=f"list_clients_{org_id}")],
               [InlineKeyboardButton(text="Пригласить клиентов", callback_data=f"invite_client_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Список клиентов организации
def build_list_clients_keyboard(clients_list, page, org_id):
    if len(clients_list) % 5 == 0:
        total_pages = len(clients_list) // 5
    else:
        total_pages = len(clients_list) // 5 + 1
    start = page * 5
    end = start + 5
    current = clients_list[start:end]
    buttons = []

    for id, name in current:
        buttons.append([InlineKeyboardButton(text=name,callback_data=f"client_chosen_{id}")])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="<=", callback_data=f"client_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="=>", callback_data=f"client_page_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"mng_clients_{org_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)