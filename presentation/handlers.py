from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import json

from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext

from app.factory import create_booking_service, create_organization_service
from app.services import OrganizationService, UserService
from app.states import RegistrationState, UserState
from infrastructure.database import get_db_pool
from infrastructure.repositories import (
    GymRepository,
    InviteRepository,
    OrganizationMemberRepository,
    OrganizationRepository,
    SettingsRepository,
    TrainingRepository,
    UserRepository,
)
import presentation.keyboards

router = Router()

_sent_notifications: set[tuple[int, int, int]] = set()


async def _notifications_worker(bot: Bot, interval_seconds: int = 60):
    """
    Фоновый воркер, который рассылает напоминания о тренировках клиентам.
    Работает через сервисы/репозитории, без прямых SQL в presentation-слое.
    """
    global _sent_notifications
    while True:
        try:
            pool = await get_db_pool()
            booking_service = create_booking_service(pool)

            # В БД используется TIMESTAMP без таймзоны, остальной код проекта тоже
            # работает от локального времени, поэтому используем datetime.now().
            now = datetime.now()
            # Максимальная комбинация настроек: до 7 дней и до 23 часов.
            horizon = now + timedelta(days=7, hours=23)
            rows = await booking_service.get_upcoming_with_settings(now, horizon)

            for row in rows:
                tg_id = row["telegram_id"]
                if not tg_id:
                    continue

                raw_settings = row["notification_settings"]
                if isinstance(raw_settings, str):
                    try:
                        settings = json.loads(raw_settings)
                    except Exception:
                        settings = {}
                else:
                    settings = dict(raw_settings or {})

                before_day = settings.get("before_day", 1)
                before_hour = settings.get("before_hour", 0)

                if before_day is None and before_hour is None:
                    continue

                training_time = row["date_start"]
                days_offset = int(before_day) if before_day is not None else 0
                hours_offset = int(before_hour) if before_hour is not None else 0
                notify_time = training_time - timedelta(days=days_offset, hours=hours_offset)

                delta = (now - notify_time).total_seconds()
                # Более надежная проверка окна отправки:
                # отправляем, только если now попадает в [notify_time, notify_time + interval_seconds)
                if notify_time <= now < notify_time + timedelta(seconds=interval_seconds):
                    key = (
                        row["booking_id"],
                        row["training_id"],
                        days_offset * 24 + hours_offset,
                    )
                    if key in _sent_notifications:
                        continue
                    _sent_notifications.add(key)

                    msg_time = training_time.strftime("%d.%m %H:%M")
                    text = f"Напоминание: у вас тренировка {msg_time}."
                    try:
                        await bot.send_message(tg_id, text)
                    except Exception:
                        continue
        except Exception:
            # Не падаем из-за одной ошибки, просто ждём следующую итерацию
            pass

        await asyncio.sleep(interval_seconds)


async def on_startup_notifications(bot: Bot):
    asyncio.create_task(_notifications_worker(bot))


# --- Клиент -----------------------------------------------------------------


async def _leave_client_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Выберите действие:", reply_markup=presentation.keyboards.build_start_keyboard())


def _client_events_book_markup(org_id: int, telegram_user_id: int):
    return presentation.keyboards.build_client_events_booking_keyboard(org_id, telegram_user_id)


async def _send_client_schedule(message: Message, state: FSMContext):
    data = await state.get_data()
    org_id = data.get("client_org_id")
    if not org_id:
        await message.answer("Сначала выберите организацию через «Войти как клиент».")
        return
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    user = await user_service.find_by_tgid(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. /start")
        return
    org_service = create_organization_service(pool)
    today = datetime.now().date()
    end = today + timedelta(days=6)
    rows = await org_service.get_schedule(user.id, org_id, today, end)
    kb = _client_events_book_markup(org_id, message.from_user.id)
    if not rows:
        await message.answer(
            "На ближайшие 7 дней нет тренировок в расписании.",
            reply_markup=kb,
        )
        return
    by_date = defaultdict(list)
    for row in rows:
        ds = row["date_start"]
        d = ds.date() if hasattr(ds, "date") else ds
        by_date[d].append(row)
    lines = ["Расписание на неделю:\n"]
    for d in sorted(by_date.keys()):
        lines.append(f"\n{d.strftime('%d.%m')}:")
        for row in sorted(by_date[d], key=lambda r: r["date_start"]):
            booked = " ✓ вы записаны" if bool(row.get("is_booked")) else ""
            tr = row.get("trainer") or "Тренер"
            spots = f"{row['available_spots']}/{row['total_spots']}"
            lines.append(
                f"  • {row['time']} — {row['type']} ({row['place']}), {tr}. Мест: {spots}{booked}"
            )
    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3490] + "\n…"
    await message.answer(text, reply_markup=kb)


async def _send_client_bookings(message: Message, state: FSMContext):
    data = await state.get_data()
    org_id = data.get("client_org_id")
    if not org_id:
        await message.answer("Сначала выберите организацию через «Войти как клиент».")
        return
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    user = await user_service.find_by_tgid(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. /start")
        return
    booking_service = create_booking_service(pool)
    now = datetime.now()
    horizon = now + timedelta(days=30)
    rows = await booking_service.get_user_bookings_in_period(user.id, org_id, now, horizon)
    if not rows:
        await message.answer("У вас нет записей на ближайшие 30 дней.")
        return
    lines = ["Ваши записи:\n"]
    for row in rows:
        ds = row["date_start"].strftime("%d.%m %H:%M")
        de = row["date_end"].strftime("%H:%M")
        tn = row.get("trainer_name") or "Тренер"
        lines.append(
            f"• {ds}–{de} — {row['type_name']}, {row['gym_name']}, {tn}"
        )
    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3490] + "\n…"
    await message.answer(text)


@router.callback_query(F.data == "client")
async def client_start_pick_org(callback: CallbackQuery, state: FSMContext):
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    user = await user_service.find_by_tgid(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройдите регистрацию: /start", show_alert=True)
        return
    org_service = OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )
    org_ids, names = await org_service.show_client_orgs(user.id)
    if not org_ids:
        await callback.answer()
        await callback.message.answer(
            "Вы не состоите ни в одной организации как клиент. "
            "Попросите у организатора ссылку-приглашение для клиентов."
        )
        return
    kb = presentation.keyboards.build_client_org_choice_keyboard(org_ids, names, 0)
    await callback.message.edit_text("Выберите организацию:", reply_markup=kb)
    await state.set_state(UserState.client_pick_org)
    await callback.answer()


@router.callback_query(F.data.startswith("client_org_page_"), StateFilter(UserState.client_pick_org))
async def client_org_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    user = await user_service.find_by_tgid(callback.from_user.id)
    org_service = OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )
    org_ids, names = await org_service.show_client_orgs(user.id)
    kb = presentation.keyboards.build_client_org_choice_keyboard(org_ids, names, page)
    await callback.message.edit_text("Выберите организацию:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("client_pick_org_"), StateFilter(UserState.client_pick_org))
async def client_pick_org_handler(callback: CallbackQuery, state: FSMContext):
    org_id = int(callback.data.rsplit("_", 1)[-1])
    pool = await get_db_pool()
    org_service = OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    user = await user_service.find_by_tgid(callback.from_user.id)
    mem = await org_service.get_membership_any_role(user.id, org_id)
    if not mem or mem.role_id != 3:
        await callback.answer("Нет доступа к этой организации", show_alert=True)
        return
    org = await org_service.get_by_id(org_id)
    await state.update_data(client_org_id=org_id)
    await state.set_state(UserState.client_menu)
    await callback.message.edit_text(
        f"Организация: {org.name}\n\n"
        "/schedule — расписание на неделю.\n"
        "/bookings — ваши записи.\n"
        "/exit — выход в главное меню.",
        reply_markup=None,
    )
    rk = presentation.keyboards.build_client_menu_reply_keyboard(org_id, callback.from_user.id)
    await callback.message.answer("Меню клиента:", reply_markup=rk)
    await callback.answer()


@router.callback_query(F.data == "client_back_to_start", StateFilter(UserState.client_pick_org))
async def client_back_from_org_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Выберите действие:", reply_markup=presentation.keyboards.build_start_keyboard())
    await callback.answer()


@router.message(Command("schedule"), StateFilter(UserState.client_menu))
async def client_cmd_schedule(message: Message, state: FSMContext):
    await _send_client_schedule(message, state)


@router.message(Command("bookings"), StateFilter(UserState.client_menu))
async def client_cmd_bookings(message: Message, state: FSMContext):
    await _send_client_bookings(message, state)


@router.message(Command("exit"), StateFilter(UserState.client_menu))
async def client_cmd_exit(message: Message, state: FSMContext):
    await _leave_client_menu(message, state)


@router.message(F.text == "Назад в меню", StateFilter(UserState.client_menu))
async def client_back_button(message: Message, state: FSMContext):
    await _leave_client_menu(message, state)


# --- Регистрация и /start ---------------------------------------------------


@router.message(CommandStart())
async def handle_start(message: types.Message, command: Command, state: FSMContext):
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    telegram_id = message.from_user.id
    user = await user_service.find_by_tgid(telegram_id)

    start_args = getattr(command, "args", None)
    if not start_args and message.text and message.text.startswith("/start"):
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            start_args = parts[1].strip()
    if start_args and start_args.startswith("join_"):
        await state.update_data(start_args=start_args)

    if user is None:
        await message.answer("Для продолжения пройдите регистрацию\nВведите ваше имя:")
        await state.set_state(RegistrationState.first_name)
    else:
        try:
            await check_invite(message, state, user.id, pool, start_args)
        except Exception:
            keyboard = presentation.keyboards.build_start_keyboard()
            await message.answer(
                "Не удалось обработать стартовую ссылку. Попробуйте еще раз.",
                reply_markup=keyboard,
            )


@router.message(RegistrationState.first_name, F.text)
async def reg_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer("Введите фамилию:")
    await state.set_state(RegistrationState.last_name)


@router.message(RegistrationState.last_name, F.text)
async def reg_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    await message.answer("Введите отчество: (при отстутствии отправьте прочерк -)")
    await state.set_state(RegistrationState.middle_name)


@router.message(RegistrationState.middle_name, F.text)
async def reg_middle_name(message: Message, state: FSMContext):
    middle_name = message.text.strip()
    if middle_name == "-":
        middle_name = None
    await state.update_data(middle_name=middle_name)
    kb = [[types.KeyboardButton(text="Отправить номер", request_contact=True)]]
    await message.answer(
        "Теперь отправьте ваш номер телефона:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=kb, resize_keyboard=True, one_time_keyboard=True
        ),
    )
    await state.set_state(RegistrationState.phone)


@router.message(RegistrationState.phone, F.contact)
async def reg_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    data = await state.get_data()
    pool = await get_db_pool()
    user_repo = UserRepository(pool)
    settings_repo = SettingsRepository(pool)
    user_service = UserService(user_repo, settings_repo)
    user = await user_service.registration(
        telegram_id=message.from_user.id,
        phone=phone,
        first_name=data["first_name"],
        last_name=data["last_name"],
        middle_name=data.get("middle_name"),
    )
    await check_invite(message, state, user.id, pool)
    await state.clear()
    await message.answer("Регистрация завершена", reply_markup=types.ReplyKeyboardRemove())


# --- Удаление организации (/delete) -----------------------------------------


@router.message(Command("delete"))
async def cmd_delete_org(message: types.Message):
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )
    user = await user_service.find_by_tgid(message.from_user.id)
    if not user:
        await message.answer(
            "Пользователь не найден. Пройдите регистрацию через /start."
        )
        return
    ids, orgs = await org_service.show_owned_orgs(user.id)
    if len(orgs) < 1:
        await message.answer("У вас нет организаций для удаления.")
    else:
        keyboard = presentation.keyboards.build_delete_org_keyboard(ids, orgs)
        await message.answer("Выберите организацию для удаления:", reply_markup=keyboard)


@router.callback_query(F.data == "start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = presentation.keyboards.build_start_keyboard()
    await callback.message.answer("Главное меню.", reply_markup=ReplyKeyboardRemove())
    await callback.message.answer("Выберите действие:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("del_org_"))
async def confirm_delete(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    keyboard = presentation.keyboards.build_confirm_delete_org(org_id)
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить организацию?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def confirm_delete_org(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(
        OrganizationRepository(pool),
        OrganizationMemberRepository(pool),
        InviteRepository(pool),
        GymRepository(pool),
        TrainingRepository(pool),
    )
    user = await user_service.find_by_tgid(callback.from_user.id)
    org = await org_service.get_by_id(org_id)
    await org_service.delete_organization(user.id, org_id)
    await callback.message.edit_text(f"Организация {org.name} успешно удалена.")
    await callback.answer()


# --- Приглашение ------------------------------------------------------------


async def check_invite(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    pool,
    direct_args=None,
):
    data = await state.get_data()
    args = (direct_args or data.get("start_args") or "").strip()

    if not args.startswith("join_"):
        keyboard = presentation.keyboards.build_start_keyboard()
        await message.answer("Выберите действие:", reply_markup=keyboard)
    else:
        invite_code = args[5:].strip()
        org_repo = OrganizationRepository(pool)
        org_member_repo = OrganizationMemberRepository(pool)
        invite_repo = InviteRepository(pool)
        org_service = OrganizationService(
            org_repo,
            org_member_repo,
            invite_repo,
            GymRepository(pool),
            TrainingRepository(pool),
        )
        try:
            role_id = await org_service.accept_invite(invite_code, user_id)
            org_id = await org_service.get_org_id_from_invite(invite_code)
            org = await org_service.get_by_id(org_id)
            role_name = {2: "тренер", 3: "клиент"}.get(role_id, "участник")
            await message.answer(f"Вы добавлены в организацию {org.name} как {role_name}!")
            try:
                new_user = await UserService(
                    UserRepository(pool), SettingsRepository(pool)
                ).get_by_id(user_id)
                new_user_name = "участник"
                if new_user:
                    new_user_name = f"{new_user.first_name} {new_user.last_name}".strip()
                owner_rows = await pool.fetch(
                    """
                    select u.telegram_id
                    from organization_member om
                    join users u on u.id = om.user_id
                    where om.organization_id = $1 and om.role_id = 1
                    """,
                    org_id,
                )
                owner_tg_ids = [r["telegram_id"] for r in owner_rows]
                notify_text = f"В организацию {org.name} добавлен {role_name}: {new_user_name}."
                for tg_id in owner_tg_ids:
                    if tg_id:
                        await message.bot.send_message(tg_id, notify_text)
            except Exception:
                pass
        except ValueError as e:
            await message.answer(f"Ошибка: {e}")
        except Exception as e:
            await message.answer(f"Не удалось присоединиться: {e}")
        await state.update_data(start_args=None)
        keyboard = presentation.keyboards.build_start_keyboard()
        await message.answer("Выберите действие:", reply_markup=keyboard)
        await state.clear()


@router.message(Command("debug"))
async def debug_state(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    await message.answer(f"Состояние: {current_state}\nДанные: {data}")
