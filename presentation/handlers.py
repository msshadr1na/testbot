
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import inline_keyboard_button, reply_keyboard_markup, reply_markup_union, users_shared, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message,WebAppInfo
from asyncpg import pool
from app.models import Gym, Organization, Role, User
from app.services import OrganizationMemberRepository, TrainingRepository, UserService, OrganizationService
from app.states import CreatingOrganizationState, RegistrationState, UserState
from infrastructure.database import get_db_pool
from infrastructure.repositories import UserRepository, SettingsRepository, OrganizationRepository, InviteRepository,GymRepository
import presentation.keyboards
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import calendar

router = Router()

from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from app.services import OrganizationService
from app.models import Training
from infrastructure.repositories import (
    TrainingRepository, OrganizationRepository, OrganizationMemberRepository,
    InviteRepository, GymRepository, UserRepository
)
from infrastructure.database import get_db_pool
import presentation.keyboards

router = Router()

@router.callback_query(F.data.startswith("calendar_"))
async def show_calendar(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    now = datetime.now()
    year, month = now.year, now.month

    pool = await get_db_pool()
    org_service = OrganizationService(
        OrganizationRepository(pool), OrganizationMemberRepository(pool),
        InviteRepository(pool), GymRepository(pool), TrainingRepository(pool)
    )
    by_day = await org_service.get_schedule_for_calendar(org_id, year, month)

    keyboard = presentation.keyboards.build_calendar_keyboard(org_id, year, month, schedule_data=by_day)
    await callback.message.edit_text(f"🗓️ Календарь: {calendar.month_name[month]} {year}", reply_markup=keyboard)


@router.callback_query(F.data.startswith("cal_prev_"))
async def prev_month(callback: CallbackQuery):
    data = callback.data.split("_")
    parts = data[2].split("-")
    if len(parts) != 2:
        await callback.answer("Неверный формат даты", show_alert=True)
        return
    year, month = map(int, parts)
    org_id = int(data[3])
    pool = await get_db_pool()
    org_service = OrganizationService(
        OrganizationRepository(pool), OrganizationMemberRepository(pool),
        InviteRepository(pool), GymRepository(pool), TrainingRepository(pool)
    )
    by_day = await org_service.get_schedule_for_calendar(org_id, year, month)
    keyboard = presentation.keyboards.build_calendar_keyboard(org_id, year, month, schedule_data=by_day)
    await callback.message.edit_text(f"🗓️ Календарь: {calendar.month_name[month]} {year}", reply_markup=keyboard)


@router.callback_query(F.data.startswith("cal_next_"))
async def next_month(callback: CallbackQuery):
    data = callback.data.split("_")
    parts = data[2].split("-")
    if len(parts) != 2:
        await callback.answer("Неверный формат даты", show_alert=True)
        return
    year, month = map(int, parts)
    org_id = int(data[3])
    pool = await get_db_pool()
    org_service = OrganizationService(
        OrganizationRepository(pool), OrganizationMemberRepository(pool),
        InviteRepository(pool), GymRepository(pool), TrainingRepository(pool)
    )
    by_day = await org_service.get_schedule_for_calendar(org_id, year, month)
    keyboard = presentation.keyboards.build_calendar_keyboard(org_id, year, month, schedule_data=by_day)
    await callback.message.edit_text(f"🗓️ Календарь: {calendar.month_name[month]} {year}", reply_markup=keyboard)


@router.callback_query(F.data.startswith("cal_day_"))
async def show_day_trainings(callback: CallbackQuery):
    parts = callback.data.split("_")
    date_str = parts[2]  # '2026-04-21'
    org_id = int(parts[3])

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    pool = await get_db_pool()
    training_repo = TrainingRepository(pool)

    trainings = await training_repo.get_trainings_by_org_and_date_range(
        org_id, target_date, target_date + timedelta(days=1)
    )

    if not trainings:
        text = f"📅 {date_str}: нет тренировок."
    else:
        lines = [f"📅 {date_str}:\n"]
        for t in trainings:
            start = t.date_start.strftime("%H:%M")
            end = t.date_end.strftime("%H:%M")

            user_repo = UserRepository(pool)
            gym_repo = GymRepository(pool)

            user = await user_repo.get_by_id(t.trainer_id)
            gym = await gym_repo.find_by_id(t.gym_id)

            trainer_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный"
            gym_name = gym.name if gym else "Неизвестный зал"

            lines.append(f"• {start}–{end} — Тренировка (зал: {gym_name}, тренер: {trainer_name})")
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓️ Календарь", callback_data=f"calendar_{org_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"calendar_{org_id}_{date_str[:7].replace('-', '_')}")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("sched_list_"))
async def show_schedule_list(callback: CallbackQuery):
    parts = callback.data.split("_")
    org_id = int(parts[2])
    page = int(parts[3])

    pool = await get_db_pool()
    training_repo = TrainingRepository(pool)

    counts = await training_repo.get_trainings_counts_by_org_grouped_by_day(
        org_id, datetime.now().date(), datetime.now().date() + timedelta(days=30)
    )
    trainings_by_day = {day: count for day, count in counts}

    total_pages = (len(trainings_by_day) + 2) // 3

    keyboard = presentation.keyboards.build_schedule_list_keyboard(org_id, trainings_by_day, page, total_pages)
    await callback.message.edit_text("📋 Расписание по дням:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("day_detail_"))
async def show_day_detail(callback: CallbackQuery):
    prefix, org_part = callback.data.rsplit("_", 1)
    org_id = int(org_part)
    parts = prefix.split("_")
    date_str = parts[2]  # '2026-04-21'

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    pool = await get_db_pool()
    training_repo = TrainingRepository(pool)

    trainings = await training_repo.get_trainings_by_org_and_date_range(
        org_id, target_date, target_date + timedelta(days=1)
    )

    if not trainings:
        text = f"📅 {date_str}: нет тренировок."
    else:
        lines = [f"📅 {date_str}:\n"]
        for t in trainings:
            start = t.date_start.strftime("%H:%M")
            end = t.date_end.strftime("%H:%M")

            user_repo = UserRepository(pool)
            gym_repo = GymRepository(pool)

            user = await user_repo.get_by_id(t.trainer_id)
            gym = await gym_repo.find_by_id(t.gym_id)

            trainer_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный"
            gym_name = gym.name if gym else "Неизвестный зал"

            lines.append(f"• {start}–{end} — Тренировка (зал: {gym_name}, тренер: {trainer_name})")
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список", callback_data=f"sched_list_{org_id}_0")],
        [InlineKeyboardButton(text="Назад", callback_data=f"sched_list_{org_id}_0")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("mng_events_"))
async def manage_events(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    keyboard = presentation.keyboards.build_manage_events_keyboard(org_id)
    await callback.message.edit_text("📅 Управление мероприятиями", reply_markup=keyboard)



# Регистрация и вход
@router.message(CommandStart())
async def handle_start(message: types.Message, command: Command, state: FSMContext):
    pool = await get_db_pool()

    userRepo = UserRepository(pool)
    settingsRepos = SettingsRepository(pool)

    user_service = UserService(userRepo, settingsRepos)

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
            await message.answer("Не удалось обработать стартовую ссылку. Попробуйте еще раз.", reply_markup=keyboard)

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
    await message.answer("Теперь отправьте ваш номер телефона:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True))
    await state.set_state(RegistrationState.phone)

@router.message(RegistrationState.phone, F.contact)
async def reg_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    data = await state.get_data()

    pool = await get_db_pool()
    user_repo = UserRepository(pool)
    settings_repo = SettingsRepository(pool)
    user_service = UserService(user_repo, settings_repo)

    user = await user_service.registration(telegram_id=message.from_user.id,phone=phone,first_name=data["first_name"],last_name=data["last_name"],middle_name=data.get("middle_name"))

    await check_invite(message, state, user.id, pool)

    await state.clear()
    await message.answer("Регистрация завершена", reply_markup=types.ReplyKeyboardRemove())

@router.message(Command("delete"))
async def start_create_note(message: types.Message):
    pool = await get_db_pool()

    user_service = UserService(UserRepository(pool),SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool),
                                      OrganizationMemberRepository(pool), InviteRepository(pool), 
                                      GymRepository(pool),TrainingRepository(pool))


    user = await user_service.find_by_tgid(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. Пройдите регистрацию используя команду /start для дальнейшего использования бота")
        return

    ids, orgs = await org_service.show_owned_orgs(user.id)

    if len(orgs) < 1:
        await message.answer("У вас нет организаций для удаления")
    else:
        keyboard = presentation.keyboards.build_delete_org_keyboard(ids,orgs)

        await message.answer("Выберите организацию для удаления:", reply_markup=keyboard)

### Обработчики кнопок

@router.callback_query(F.data.startswith("start"))
async def cancel_delete_org(callback: CallbackQuery):
    keyboard = presentation.keyboards.build_start_keyboard()
    await callback.message.edit_text("Войти как:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_org_"))
async def confirm_delete(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    keyboard = presentation.keyboards.build_confirm_delete_org(org_id)
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить организацию?", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_"))
async def confirm_delete_org(callback: CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    
    pool = await get_db_pool()
    user_repo = UserRepository(pool)
    org_repo = OrganizationRepository(pool)
    org_member_repo = OrganizationMemberRepository(pool)
    user_service = UserService(user_repo, SettingsRepository(pool))
    org_service = OrganizationService(org_repo, org_member_repo, InviteRepository(pool),
                                     GymRepository(pool),TrainingRepository(pool))

    user = await user_service.find_by_tgid(callback.from_user.id)
    org = await org_service.get_by_id(org_id)

    await org_service.delete_organization(user.id, org_id)
    await callback.message.edit_text(f"Организация {org.name} успешно удалена.")

    await callback.answer()

#Войти как организатор
@router.callback_query(F.data.startswith("owner"))
async def as_org(callback: CallbackQuery, state):
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool),OrganizationMemberRepository(pool), 
                                      InviteRepository(pool),GymRepository(pool),TrainingRepository(pool))
    user = await user_service.find_by_tgid(callback.from_user.id)
    ids, names = await org_service.show_owned_orgs(user.id)


    keyboard = await presentation.keyboards.build_org_keyboard(ids, names)
    await callback.message.edit_text("Вы вошли как организатор\nВыберите организацию или создайте новую",reply_markup=keyboard)
    await callback.answer()
    await state.set_state(UserState.organization)


@router.callback_query(F.data == "create_org")
async def start_create_org(callback: types.CallbackQuery,state: FSMContext):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    await callback.message.answer("Введите название для будущей организации:")

    await callback.answer()
    await state.set_state(CreatingOrganizationState.name)

#Выбор организации для управления
@router.callback_query(F.data.startswith("choose_org_"))
async def choose_org(callback: types.CallbackQuery, state):
    org_id = int(callback.data.split("_")[-1])

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    name = await org_service.get_by_id(org_id)

    keyboard = presentation.keyboards.build_manage_org_keyboard(org_id)

    await callback.message.edit_text(f"Организация {name.name}:", reply_markup=keyboard)
    await state.set_state(UserState.menu)
    await state.update_data(selected_org_id=org_id)

#Раздел управления организацией
@router.callback_query(F.data.startswith("edit_org_"))
async def edit_org(callback: types.CallbackQuery, state):
    org_id = int(callback.data.split("_")[-1])
    await state.set_state(UserState.menu)
    keyboard = presentation.keyboards.build_edit_org_keyboard(org_id)
    await callback.message.edit_text("Редактирование организации", reply_markup=keyboard)

#Редактирование названия организации
@router.callback_query(F.data.startswith("edit_name_org"))
async def edit_org_name(callback: types.CallbackQuery, state):
    org_id = int(callback.data.split("_")[-1])
    await state.update_data(editing_org_id=org_id)
    keyboard = presentation.keyboards.build_edit_name_org_keyboard(org_id)
    await callback.message.edit_text("Введите новое название организации:", reply_markup=keyboard)
    await state.set_state(UserState.editing_org_name)

@router.message(UserState.editing_org_name, F.text)
async def edit_org_name(message: Message, state: FSMContext):
    name=message.text.strip()
    data = await state.get_data()
    org_id = data.get("editing_org_id")

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool),GymRepository(pool),TrainingRepository(pool))

    is_created = await org_service.find_by_name(name)
    
    if is_created:
        await message.answer(
            f"Организация с названием {name} уже существует.\nВведите другое название:")
    else:
        await org_service.update_name(org_id, name)
        await message.answer(f"Название организации успешно изменено на {name}")
        await state.update_data(editing_org_id=None)
        await message.answer("Редактированиее организации", reply_markup=presentation.keyboards.build_edit_org_keyboard(org_id))

    await state.set_state(UserState.organization)
    await state.update_data(selected_org_id=org_id)

#Раздел управления помещениями организации
@router.callback_query(F.data.startswith("manage_places_"))
async def manage_places(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    keyboard = presentation.keyboards.build_manage_places_keyboard(org_id)

    await callback.message.edit_text("Управление помещениями", reply_markup=keyboard)

#Добавление нового помещения
@router.callback_query(F.data.startswith("add_place_"))
async def add_place(callback: types.CallbackQuery, state: FSMContext):
    org_id = int(callback.data.split("_")[-1])
    keyboard = presentation.keyboards.build_add_place(org_id) #^

    await state.set_state(UserState.creating_place)
    await state.update_data(selected_org_id=org_id)

#Просмотреть помещения организации
@router.callback_query(F.data.startswith("list_places_"))
async def list_places(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    places_list = await org_service.get_places_list(org_id)
    if places_list:
        keyboard = presentation.keyboards.build_list_places_keyboard(places_list, 0, org_id)
        await callback.message.edit_text(f"Список помещений:", reply_markup=keyboard)
    else:
        keyboard = presentation.keyboards.build_list_places_keyboard(places_list, 0, org_id)
        await callback.message.edit_text(f"Помещений нет. Добавьте их в свою организацию в разделе управления помещениями.", reply_markup=keyboard)

#Просмотреть страницу списка помещений
@router.callback_query(F.data.startswith("place_page_"))
async def list_places_pages(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    org_id = data.get("selected_org_id")
    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    places_list = await org_service.get_places_list(org_id)
    keyboard = presentation.keyboards.build_list_places_keyboard(places_list, page, org_id)
    await callback.message.edit_text(f"Список помещений (страница {page + 1}):", reply_markup=keyboard)

#Редактирование названия помещения организации
@router.callback_query(F.data.startswith("edit_name_place_"))
async def edit_place_name(callback: types.CallbackQuery, state):
    place_id = int(callback.data.split("_")[-1])
    await state.update_data(editing_place_id=place_id)
    keyboard = presentation.keyboards.build_edit_place_name_keyboard(place_id)
    await callback.message.edit_text("Введите новое название помещения:", reply_markup=keyboard)######## Продумать логику, чтобы хотя бы одно помещение всегда было!!!! И в начале чтоб создавалось однооооооооооооооооо
    await state.set_state(UserState.editing_org_name)

#Карточка помещения организации
@router.callback_query(F.data.startswith("place_chosen_"))
async def choose_place(callback: types.CallbackQuery, state: FSMContext):
    place_id = int(callback.data.split("_")[-1])
    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    place = await org_service.get_place_by_id(place_id)
    keyboard = presentation.keyboards.build_manage_place_keyboard(place_id)
    await callback.message.edit_text(f"Помещение:\n\nНазвание: {place.name}", reply_markup=keyboard)


#
#Раздел работники
#
@router.callback_query(F.data.startswith("mng_workers_"))
async def manage_workers(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    keyboard = presentation.keyboards.build_manage_workers_keyboard(org_id)
    
    await callback.message.edit_text("Управление работниками", reply_markup=keyboard)

#Просмотр списка работников организации
@router.callback_query(F.data.startswith("list.workers_"))
async def list_workers_first_page(callback: types.CallbackQuery, state: FSMContext):
    org_id = int(callback.data.split("_")[-1])
    await state.update_data(selected_org_id=org_id)
    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    workers_list = await org_service.get_workers_list(org_id)

    if workers_list:
        keyboard = presentation.keyboards.build_list_workers_keyboard(workers_list, 0 ,org_id)
        await callback.message.edit_text(f"Список работников (страница 1):", reply_markup=keyboard)
    else:
        keyboard = presentation.keyboards.build_list_workers_keyboard(workers_list, 0 ,org_id)
        await callback.message.edit_text(f"Работников нет. Добавьте их в свою организацию при помощи ссылки-приглашения", reply_markup=keyboard)

@router.callback_query(F.data.startswith("wrk.page_"))
async def list_workers_pages(callback: types.CallbackQuery, state):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    org_id = data.get("selected_org_id")

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    workers_list = await org_service.get_workers_list(org_id)

    keyboard = presentation.keyboards.build_list_workers_keyboard(workers_list, page ,org_id)
    await callback.message.edit_text(f"Список работников (страница {page + 1}):", reply_markup=keyboard)

#Управление работником
@router.callback_query(F.data.startswith("worker_chosen_"))
async def choose_worker(callback, state: FSMContext):
     wrk_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))

     worker = await user_service.get_by_id(wrk_id)
     
     keyboard = presentation.keyboards.build_manage_worker_keyboard(wrk_id)

     if worker.middle_name:
        await callback.message.edit_text(f"Работник:\n\nИмя: {worker.first_name} {worker.last_name} {worker.middle_name}\n\nНомер телефона: {worker.phone}", reply_markup=keyboard)
     else:
        await callback.message.edit_text(f"Работник:\n\nИмя: {worker.first_name} {worker.last_name}\n\nНомер телефона: {worker.phone}", reply_markup=keyboard)

#Подтверждение удаления работника из организации
@router.callback_query(F.data.startswith("del_worker_"))
async def delete_worker(callback, state: FSMContext):
     wrk_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     organization_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                                InviteRepository(pool),GymRepository(pool),TrainingRepository(pool))
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))

     data = await state.get_data()
     org_id = data.get("selected_org_id")
     org_id = int(callback.data.split("_")[-1])
     worker = await user_service.get_by_id(wrk_id)

     keyboard = presentation.keyboards.build_confirm_delete_worker(wrk_id)
    
     await callback.message.edit_text(f"Вы уверены, что хотите удалить {worker.first_name} {worker.last_name} из организации?", reply_markup=keyboard)

#Удаление работника из организации
@router.callback_query(F.data.startswith("wrk_confirm_del_"))
async def confirm_delete_worker(callback, state: FSMContext):
     wrk_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     organization_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                                InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))
     worker = await user_service.get_by_id(wrk_id)
     data = await state.get_data()
     org_id = data.get("selected_org_id")
     await organization_service.delete_worker(org_id, wrk_id)

     await callback.message.edit_text(f"Работник {worker.first_name} {worker.last_name} успешно удалён из организации")
     keyboard = presentation.keyboards.build_manage_workers_keyboard(org_id)
     await callback.message.answer(f"Управление работниками", reply_markup=keyboard)


#Приглашение работников в организацию (создание ссылки-приглашения)
@router.callback_query(F.data.startswith("invite.worker_"))
async def invite_worker(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    role_id = 2

    pool = await get_db_pool()
    invite_repo = InviteRepository(pool)
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))

    link = await org_service.get_or_create_invite(org_id, role_id)

    keyboard = presentation.keyboards.build_invite_workers_keyboard(org_id)

    await callback.message.edit_text(f"Приглашение для работников:\n\n`{link}`\n\nНажмите на ссылку, чтобы скопировать", parse_mode="MarkdownV2", reply_markup=keyboard)

#Обновление ссылки-приглашения для работников
@router.callback_query(F.data.startswith("upd.code2_"))
async def update_invite_worker(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    role_id = 2

    pool = await get_db_pool()
    invite_repo = InviteRepository(pool)
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))

    link = await org_service.update_invite(org_id, role_id)

    keyboard = presentation.keyboards.build_invite_workers_keyboard(org_id)

    await callback.message.edit_text(f"Приглашение для работников:\n\n`{link}`\n\nНажмите на ссылку, чтобы скопировать", parse_mode="MarkdownV2", reply_markup=keyboard)
  
#
#Раздел клиенты
#
@router.callback_query(F.data.startswith("mng_clients_"))
async def manage_workers(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    keyboard = presentation.keyboards.build_manage_clients_keyboard(org_id)
    
    await callback.message.edit_text("Управление клиентами", reply_markup=keyboard)

#Просмотр списка клиентов организации
@router.callback_query(F.data.startswith("list_clients_"))
async def list_clients_first_page(callback: types.CallbackQuery, state: FSMContext):
    org_id = int(callback.data.split("_")[-1])
    await state.update_data(selected_org_id=org_id)
    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    clients_list = await org_service.get_clients_list(org_id)

    if clients_list:
        keyboard = presentation.keyboards.build_list_clients_keyboard(clients_list, 0 ,org_id)
        await callback.message.edit_text(f"Список клиентов (страница 1):", reply_markup=keyboard)
    else:
        keyboard = presentation.keyboards.build_list_clients_keyboard(clients_list, 0 ,org_id)
        await callback.message.edit_text(f"Клиентов нет. Добавьте их в свою организацию при помощи ссылки-приглашения", reply_markup=keyboard)

@router.callback_query(F.data.startswith("client_page_"))
async def list_clients_pages(callback: types.CallbackQuery, state):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    org_id = data.get("selected_org_id")

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
    clients_list = await org_service.get_clients_list(org_id)

    keyboard = presentation.keyboards.build_list_clients_keyboard(clients_list, page ,org_id)
    await callback.message.edit_text(f"Список клиентов (страница {page + 1}):", reply_markup=keyboard)

#Приглашение клиентов в организацию (создание ссылки-приглашения)
@router.callback_query(F.data.startswith("invite_client_"))
async def invite_client(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    role_id = 3

    pool = await get_db_pool()
    invite_repo = InviteRepository(pool)
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                     InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))

    link = await org_service.get_or_create_invite(org_id, role_id)

    keyboard = presentation.keyboards.build_invite_clients_keyboard(org_id)

    await callback.message.edit_text(f"Приглашение для клиентов:\n\n`{link}`\n\nНажмите на ссылку, чтобы скопировать", parse_mode="MarkdownV2", reply_markup=keyboard)

#Обновление ссылки-приглашения для клиентов
@router.callback_query(F.data.startswith("upd_code3_"))
async def update_invite_client(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    role_id = 3     

    pool = await get_db_pool()
    invite_repo = InviteRepository(pool)
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), 
                                      InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))

    link = await org_service.update_invite(org_id, role_id)

    keyboard = presentation.keyboards.build_invite_clients_keyboard(org_id)

    await callback.message.edit_text(f"Приглашение для клиентов:\n\n`{link}`\n\nНажмите на ссылку, чтобы скопировать", parse_mode="MarkdownV2", reply_markup=keyboard)

#Управление клиентом
@router.callback_query(F.data.startswith("client_chosen_"))
async def choose_client(callback, state: FSMContext):
     client_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))

     client = await user_service.get_by_id(client_id)
     
     keyboard = presentation.keyboards.build_manage_client_keyboard(client_id)

     if client.middle_name:
        await callback.message.edit_text(f"Клиент:\n\nИмя: {client.first_name} {client.last_name} {client.middle_name}\n\nНомер телефона: {client.phone}", reply_markup=keyboard)
     else:
        await callback.message.edit_text(f"Клиент:\n\nИмя: {client.first_name} {client.last_name}\n\nНомер телефона: {client.phone}", reply_markup=keyboard)

#Подтверждение удаления клиента из организации
@router.callback_query(F.data.startswith("del_client_"))
async def delete_client(callback, state: FSMContext):
     client_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     organization_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                               InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))

     data = await state.get_data()
     org_id = data.get("selected_org_id")
     org_id = int(callback.data.split("_")[-1])
     client = await user_service.get_by_id(client_id)

     keyboard = presentation.keyboards.build_confirm_delete_client(client_id)
    
     await callback.message.edit_text(f"Вы уверены, что хотите удалить {client.first_name} {client.last_name} из организации?", reply_markup=keyboard)

#Удаление клиента из организации
@router.callback_query(F.data.startswith("client_confirm_del_"))
async def confirm_delete_client(callback, state: FSMContext):
     client_id = int(callback.data.split("_")[-1])

     pool = await get_db_pool()
     organization_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                               InviteRepository(pool), GymRepository(pool),
                                               TrainingRepository(pool))
     user_service = UserService(UserRepository(pool),SettingsRepository(pool))
     client = await user_service.get_by_id(client_id)
     data = await state.get_data()
     org_id = data.get("selected_org_id")
     await organization_service.delete_client(org_id, client_id)

     await callback.message.edit_text(f"Клиент {client.first_name} {client.last_name} успешно удалён из организации")
     keyboard = presentation.keyboards.build_manage_clients_keyboard(org_id)
     await callback.message.answer(f"Управление клиентами", reply_markup=keyboard)


# Текстовые сообщения



## Вспомогательные функции

#Создание организации
@router.message(CreatingOrganizationState.name, F.text)
async def handle_create_organization(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()

    pool = await get_db_pool()
    organizationRepo = OrganizationRepository(pool)
    organizationMemberRepo = OrganizationMemberRepository(pool)
    userRepo = UserRepository(pool)
    settingsRepos = SettingsRepository(pool)
    user_service = UserService(userRepo, settingsRepos)
    organization_service = OrganizationService(organizationRepo, organizationMemberRepo,InviteRepository(pool),
                                              GymRepository(pool),TrainingRepository(pool))

    user = await user_service.find_by_tgid(user_id)
    is_created = await organization_service.find_by_name(name)

    if is_created is None:
        organization = await organization_service.create_organization(user, name)
        await message.answer("Введите название для основного(первого) помещения новой организации:\n\n*Можно будет добавить ещё помещения в разделе управления организацией:")
        await state.set_state(CreatingOrganizationState.place_name)
        await state.update_data(org_id = organization.id)
    else:
        await message.answer(
            f"Организация с названием {name} уже существует.\n"
            "Введите другое название:"
        )

@router.message(CreatingOrganizationState.place_name, F.text)
async def handle_create_first_place(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    data = await state.get_data()

    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    organization_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool),
                                               InviteRepository(pool), GymRepository(pool),TrainingRepository(pool))

    user = await user_service.find_by_tgid(user_id)
    org_id = data.get("org_id")
    org = await organization_service.get_by_id(org_id)
    new_place = await organization_service.create_place(org_id,name)
    await message.answer(f"Организация {org.name} с помещением {name} успешно создана")
    keyboard = presentation.keyboards.build_manage_org_keyboard(org_id)
    await message.answer("Управление организацией:", reply_markup=keyboard)
    await state.set_state(UserState.menu)
    await state.update_data(selected_org_id = org_id)

    

#Проверка наличия приглашения при входе, и его обработка
async def check_invite(message: types.Message,state: FSMContext, user_id: int, pool, direct_args=None):
    data = await state.get_data()
    args = (direct_args or data.get("start_args") or "").strip()

    if not args.startswith("join_"):
        keyboard = presentation.keyboards.build_start_keyboard()
        await message.answer("Войти как:", reply_markup=keyboard)
    else:
        invite_code = args[5:].strip()

        org_repo = OrganizationRepository(pool)
        org_member_repo = OrganizationMemberRepository(pool)
        invite_repo = InviteRepository(pool)
        org_service = OrganizationService(org_repo, org_member_repo, invite_repo,GymRepository(pool),TrainingRepository(pool))
    
        try:
            role_id = await org_service.accept_invite(invite_code, user_id)
            org_id = await org_service.get_org_id_from_invite(invite_code)
            org = await org_service.get_by_id(org_id)
            role_name = {2: "тренер", 3: "клиент"}.get(role_id, "участник")
            await message.answer(f"Вы добавлены в организацию {org.name} как {role_name}!")

            # Уведомляем организаторов о новом участнике
            try:
                new_user = await UserService(UserRepository(pool), SettingsRepository(pool)).find_by_tgid(user_id)
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
        await message.answer("Войти как:", reply_markup=keyboard)
        await state.clear()
        await state.set_state(UserState.role)

@router.message(Command("debug"))
async def debug_state(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    await message.answer(f"Состояние: {current_state}\nДанные: {data}")