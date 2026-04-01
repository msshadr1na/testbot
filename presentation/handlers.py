from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import inline_keyboard_button, reply_keyboard_markup, reply_markup_union, users_shared, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from asyncpg import pool
from app.models import Organization, User
from app.services import OrganizationMemberRepository, UserService, OrganizationService
from infrastructure.database import get_db_pool
from infrastructure.repositories import UserRepository, SettingsRepository, OrganizationRepository, InviteRepository
import presentation.keyboards

router = Router()

waiting_for_name = set()
waiting_for_org_num = set()
waiting_for_delete_confirm = set()

# Команды
@router.message(CommandStart())
async def handle_start(message: types.Message, command: Command):
    pool = await get_db_pool()

    userRepo = UserRepository(pool)
    settingsRepos = SettingsRepository(pool)

    user_service = UserService(userRepo, settingsRepos)

    user_id = message.from_user.id
    user = await user_service.find_by_tgid(user_id)
    
    # Если пользователь новый — регистрируем
    if user is None:
        if message.from_user.last_name is None:
            last_name = "Фамилия"
        else:
            last_name = message.from_user.last_name
        user = await user_service.registration(
            user_id, 
            None, 
            message.from_user.first_name, 
            last_name, 
            None
        )

    # Проверяем, есть ли аргументы (приглашение)
    args = command.args
    if args and args.startswith("join_"):
        invite_code = args[len("join_"):]
        
        # Подключаем репозитории для обработки приглашения
        org_repo = OrganizationRepository(pool)
        org_member_repo = OrganizationMemberRepository(pool)
        invite_repo = InviteRepository(pool)
        org_service = OrganizationService(org_repo, org_member_repo, invite_repo)
        
        try:
            role_id = await org_service.accept_invite(invite_code, user.id)
            role_name = {2: "тренер", 3: "клиент"}.get(role_id, "участник")
            await message.answer(f" Вы добавлены в организацию как {role_name}!")
        except ValueError as e:
            await message.answer(f"Ошибка: {e}")
        except Exception as e:
            await message.answer(f"Не удалось присоединиться: {e}")
        
        # После обработки приглашения — показываем обычное меню
        keyboard = presentation.keyboards.build_start_keyboard()
        await message.answer(f"Добро пожаловать, {user.first_name}!\nВойти как:", reply_markup=keyboard)
        return

    # Обычный старт — без приглашения
    keyboard = presentation.keyboards.build_start_keyboard()
    await message.answer(f"Добро пожаловать, {user.first_name}!\nВойти как:", reply_markup=keyboard)

@router.message(Command("create"))
async def start_create_note(message: types.Message):
    waiting_for_name.add(message.from_user.id)
    
    await message.answer("Введите название для будущей организации:")

@router.message(Command("delete"))
async def start_create_note(message: types.Message):
    pool = await get_db_pool()

    user_service = UserService(UserRepository(pool),SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool),OrganizationMemberRepository(pool), InviteRepository(pool))


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

# Обработчики кнопок

@router.callback_query(F.data.startswith("start"))
async def cancel_delete_org(callback: CallbackQuery):
    keyboard = presentation.keyboards.build_start_keyboard()
    await callback.message.answer("Войти как:", reply_markup=keyboard)


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
    org_service = OrganizationService(org_repo, org_member_repo, InviteRepository(pool))

    user = await user_service.find_by_tgid(callback.from_user.id)
    org = await org_service.get_by_id(org_id)

    await org_service.delete_organization(user.id, org_id)
    await callback.message.edit_text(f"Организация {org.name} успешно удалена.")

    await callback.answer()

@router.callback_query(F.data.startswith("cancel_del"))
async def cancel_delete_org(callback: CallbackQuery):
    await callback.message.edit_text(f"Организация не была удалена.")
    await callback.answer()

#Войти как организатор
@router.callback_query(F.data.startswith("owner"))
async def as_org(callback: CallbackQuery):
    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool),OrganizationMemberRepository(pool), InviteRepository(pool))

    user = await user_service.find_by_tgid(callback.from_user.id)
    ids, names = await org_service.show_owned_orgs(user.id)

    keyboard = await presentation.keyboards.build_org_keyboard()
    await callback.message.edit_text("Вы вошли как организатор\nВыберите организацию или создайте новую",reply_markup=keyboard)
    await callback.answer()

#Выбор организации для управления
@router.callback_query(F.data.startswith("choose.org_"))
async def choose_org(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), InviteRepository(pool))
    name = await org_service.get_by_id(org_id)

    keyboard = presentation.keyboards.build_manage_org_keyboard(org_id)

    await callback.message.edit_text(f"Организация {name.name}", reply_markup=keyboard)

@router.callback_query(F.data.startswith("orgs"))
async def choose_org(callback):

    pool = await get_db_pool()
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool),OrganizationMemberRepository(pool), InviteRepository(pool))

    user = await user_service.find_by_tgid(callback.from_user.id)
    ids, names = await org_service.show_owned_orgs(user.id)

    if len(names) < 1:
        keyboard = presentation.keyboards.build_zero_orgs_keyboard()
        await callback.message.edit_text("У вас нет организаций", reply_markup=keyboard)
    else:
        keyboard = presentation.keyboards.build_choose_org_keyboard(ids,names)
        await callback.message.edit_text("Выберите организацию:", reply_markup=keyboard)

@router.callback_query(F.data == "create_org")
async def start_create_org(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    waiting_for_name.add(user_id)
    await callback.message.delete()
    
    await callback.message.answer("Введите название для будущей организации:")

    await callback.answer()



@router.callback_query(F.data.startswith("choose.org_"))
async def choose_org(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    pool = await get_db_pool()
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), InviteRepository(pool))
    name = await org_service.get_by_id(org_id)

    keyboard = presentation.keyboards.build_manage_org_keyboard(org_id)

    await callback.message.edit_text(f"Организация {name.name}", reply_markup=keyboard)

@router.callback_query(F.data.startswith("mng.workers_"))
async def manage_workers(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])

    keyboard = presentation.keyboards.build_manage_workers_keyboard(org_id)
    
    await callback.message.edit_text("Управление работниками", reply_markup=keyboard)

@router.callback_query(F.data.startswith("invite.worker_"))
async def invite_worker(callback: types.CallbackQuery):
    org_id = int(callback.data.split("_")[-1])
    role_id = 2

    pool = await get_db_pool()
    invite_repo = InviteRepository(pool)
    user_service = UserService(UserRepository(pool), SettingsRepository(pool))
    org_service = OrganizationService(OrganizationRepository(pool), OrganizationMemberRepository(pool), InviteRepository(pool))

    user = await user_service.find_by_tgid(callback.message.from_user.id)

    link = await org_service.get_or_create_invite(org_id, 2)

    keyboard = presentation.keyboards.build_invite_code_keyboard(link, org_id)

    await callback.message.edit_text(f"Приглашение для работников:\n{link}", reply_markup=keyboard)
   



# Текстовые сообщения
@router.message()
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id    

    if user_id in waiting_for_name:
        await handle_create_organization(message)
        return
    
    await message.answer("Неизвестная команда. Используйте /create или /delete.")


# Вспомогательные функции
async def handle_create_organization(message: types.Message):
    user_id = message.from_user.id
    name = message.text

    pool = await get_db_pool()
    organizationRepo = OrganizationRepository(pool)
    organizationMemberRepo = OrganizationMemberRepository(pool)
    userRepo = UserRepository(pool)
    settingsRepos = SettingsRepository(pool)
    user_service = UserService(userRepo, settingsRepos)
    organization_service = OrganizationService(organizationRepo, organizationMemberRepo,InviteRepository(pool))

    user = await user_service.find_by_tgid(user_id)
    is_created = await organization_service.find_by_name(name)

    if is_created is None:
        organization = await organization_service.create_organization(user, name)
        waiting_for_name.remove(user_id)
        keyboard = await presentation.keyboards.build_org_keyboard()
        await message.answer(f"Организация {name} успешно создана")
        await message.answer("Вы вошли как организатор", reply_markup=keyboard)
    else:
        await message.answer(
            f"Организация с названием {name} уже существует.\n"
            "Введите другое название:"
        )

