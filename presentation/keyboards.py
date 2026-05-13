from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from config import web_app_base_url


def build_start_keyboard():
    web_entry = f"{web_app_base_url}/app/client_orgs.html"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Войти как клиент", callback_data="client")],
            [InlineKeyboardButton(text="Перейти в веб-приложение", web_app=WebAppInfo(url=web_entry))],
        ]
    )


def build_client_org_choice_keyboard(org_ids: list, names: list, page: int):
    pairs = list(zip(org_ids, names))
    per_page = 5
    total_pages = max(1, (len(pairs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    chunk = pairs[start : start + per_page]

    buttons = []
    for org_id, name in chunk:
        buttons.append(
            [InlineKeyboardButton(text=name, callback_data=f"client_pick_org_{org_id}")]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="<=", callback_data=f"client_org_page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="=>", callback_data=f"client_org_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="Назад", callback_data="client_back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_client_menu_reply_keyboard(org_id: int, telegram_user_id: int):
    web_url = f"{web_app_base_url}/app/client_main.html?org_id={org_id}&user_id={telegram_user_id}&v=2"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Управление в веб-приложении", web_app=WebAppInfo(url=web_url))],
            [KeyboardButton(text="Назад в меню")],
        ],
        resize_keyboard=True,
    )


def build_delete_org_keyboard(org_ids, names):
    buttons = []
    for org_id, name in zip(org_ids, names):
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"del_org_{org_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_confirm_delete_org(org_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Удалить", callback_data=f"confirm_del_{org_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data="start")],
        ]
    )


def build_client_events_booking_keyboard(org_id: int, telegram_user_id: int):
    url = f"{web_app_base_url}/app/client_events.html?org_id={org_id}&user_id={telegram_user_id}&v=2"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться на тренировку", web_app=WebAppInfo(url=url))],
        ]
    )
