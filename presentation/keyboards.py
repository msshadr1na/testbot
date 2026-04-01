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
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"select_org_{org_id}")])
    
    buttons.append([InlineKeyboardButton(text="Создать организацию",callback_data="create_org")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="start")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_zero_orgs_keyboard():
    buttons=[[InlineKeyboardButton(text="Назад", callback_data="owner")]]
    keyboard=InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_choose_org_keyboard(orgs,names):
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"choose.org_{org_id}")] for org_id, name in zip(orgs,names)]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="owner")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_manage_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Редактировать организацию", callback_data=f"edit.org_{org_id}")],
               [InlineKeyboardButton(text="Управление работниками", callback_data=f"mng.workers_{org_id}")],
               [InlineKeyboardButton(text="Управление клиентами", callback_data=f"mng.clients_{org_id}")],
               [InlineKeyboardButton(text="Управление мероприятиями", callback_data=f"mng.events_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data="orgs")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_manage_workers_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Список работников", callback_data="list_workers")],
               [InlineKeyboardButton(text="Удалить работника", callback_data="del_worker")],
               [InlineKeyboardButton(text="Пригласить работников", callback_data=f"invite.worker_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"choose.org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_invite_workers_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Ссылка-приглашение", callback_data=f"get.code2_{org_id}")],
               [InlineKeyboardButton(text="Обновить ссылку-приглашение", callback_data=f"upd.code2_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"mng.workers_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_invite_code_keyboard(invite_code,org_id):
    buttons = [[InlineKeyboardButton(text="Скопировать ссылку-приглашение", callback_data=f"copy.code_{invite_code}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"invite.worker_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_delete_org_keyboard(orgs,names):
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"del_org_{org_id}")] for org_id, name in zip(orgs,names)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def build_confirm_delete_org(org_id):
    buttons = [[InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_del_{org_id}")],
               [InlineKeyboardButton(text="Отмена", callback_data="cancel_del")]]
    print(buttons)
    keyboard = InlineKeyboardMarkup(inline_keyboard = buttons)
    return keyboard
