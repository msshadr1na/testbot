from aiogram.types import inline_keyboard_button, keyboard_button, users_shared, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from app.models import User
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

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

#Клавиатура для управления организацией
def build_manage_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Настройки", callback_data=f"edit_org_{org_id}")],
               [InlineKeyboardButton(text="Помещения", callback_data=f"manage_places_{org_id}")],
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
               [InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для управления помещениями организации
def build_manage_places_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Просмотреть помещения", callback_data=f"list_places_{org_id}")],
               [InlineKeyboardButton(text="Добавить помещение", callback_data=f"add_place_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для отмены редактирования названия организации
def build_edit_name_org_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Отмена", callback_data=f"edit_org_{org_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#Клавиатура для списка помещений организации
def build_list_places_keyboard(places_list, page, org_id):
    total_pages = (len(places_list) + 4) // 5
    start = page * 5
    end = start + 5
    current = places_list[start:end]
    buttons = []
    for id, name in current:
        buttons.append([InlineKeyboardButton(text=name,callback_data=f"place_chosen_{id}")])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="<=", callback_data=f"place_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="=>", callback_data=f"place_page_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"manage_places_{org_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#Клавиатура для управления конкретным помещением организации
def build_manage_place_keyboard(place_id):
    buttons = [[InlineKeyboardButton(text="Редактировать название", callback_data=f"edit_name_place_{place_id}")],###
               [InlineKeyboardButton(text="Удалить помещение", callback_data=f"del_place_{place_id}")],###
               [InlineKeyboardButton(text="Назад", callback_data=f"place_page_0")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Клавиатура для редактирования названия помещения
def build_edit_place_name_keyboard(place_id):
    buttons = [[InlineKeyboardButton(text="Отмена", callback_data=f"place_chosen_{place_id}")]]
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

def build_invite_clients_keyboard(org_id):
    buttons = [[InlineKeyboardButton(text="Обновить ссылку-приглашение", callback_data=f"upd_code3_{org_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"mng_clients_{org_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Управление конкретным клиентом организации
def build_manage_client_keyboard(client_id):
    buttons = [[InlineKeyboardButton(text="Удалить", callback_data=f"del_client_{client_id}")],
               [InlineKeyboardButton(text="Расписание клиента", callback_data=f"client_schedule_{client_id}")],
               [InlineKeyboardButton(text="Назад", callback_data=f"client_page_0")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

#Удаление клиента из организации
def build_confirm_delete_client(client_id):
    buttons = [[InlineKeyboardButton(text="Удалить", callback_data=f"client_confirm_del_{client_id}")],
               [InlineKeyboardButton(text="Отмена", callback_data=f"client_chosen_{client_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard = buttons)
    return keyboard




def build_manage_events_keyboard(org_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓️ Календарь", callback_data=f"calendar_{org_id}")],
        [InlineKeyboardButton(text="📋 Список", callback_data=f"sched_list_{org_id}_0")],
        [InlineKeyboardButton(text="Создать тренировку", callback_data=f"add_training_{org_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")]
    ])
    return keyboard


#Создание календаря с тренировками
def build_calendar_keyboard(org_id: int, year: int, month: int, schedule_data: dict = None):
    month_name = calendar.month_name[month]
    cal = calendar.monthcalendar(year, month)

    date_buttons = []
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                count = schedule_data.get(datetime.date(year, month, day),0)

                if count == 0:
                    text = str(day)
                elif 1 <= count <= 2:
                    text = f"🟡 {day}"
                elif 3 <= count <= 5:
                    text = f"🟠 {day}"
                else:
                    text = f"🔴 {day}"

                week_buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=f"cal_day_{date_key}_{org_id}"
                ))
        date_buttons.append(week_buttons)

    # ... остальная часть клавиатуры (навигация) ...
    prev_month = (month - 2) % 12 + 1
    prev_year = year if month > 1 else year - 1
    next_month = (month % 12) + 1
    next_year = year if month < 12 else year + 1

    nav_buttons = [
        [
            InlineKeyboardButton(text="◀️", callback_data=f"cal_prev_{prev_year}-{prev_month:02d}_{org_id}"),
            InlineKeyboardButton(text=month_name, callback_data="ignore"),
            InlineKeyboardButton(text="▶️", callback_data=f"cal_next_{next_year}-{next_month:02d}_{org_id}")
        ],
        [
            InlineKeyboardButton(text="📊 Анализ", callback_data=f"analytics_{org_id}"),
            InlineKeyboardButton(text="📋 Список", callback_data=f"sched_list_{org_id}_0")
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=date_buttons + nav_buttons)

def build_schedule_list_keyboard(org_id: int, trainings_by_day: dict, page: int, total_pages: int):
    buttons = []

    # Сортируем дни
    sorted_days = sorted(trainings_by_day.keys())

    # Показываем 3 дня за раз
    start_idx = page * 3
    end_idx = min(start_idx + 3, len(sorted_days))
    current_days = sorted_days[start_idx:end_idx]

    for day in current_days:
        day_str = day.strftime("%d.%m")
        buttons.append([InlineKeyboardButton(
            text=f"📅 {day_str}",
            callback_data=f"day_detail_{day.strftime('%Y-%m-%d')}_{org_id}"
        )])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"sched_list_{org_id}_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"sched_list_{org_id}_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🗓️ Календарь", callback_data=f"calendar_{org_id}"),
        InlineKeyboardButton(text="📊 Анализ", callback_data=f"analytics_{org_id}")
    ])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"choose_org_{org_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)