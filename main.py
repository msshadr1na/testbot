from aiogram import Bot, Dispatcher
from presentation.handlers import router, on_startup_notifications
from config import bot_token

bot = Bot(token = bot_token)
dp = Dispatcher()
dp.include_router(router)


async def main():
    dp.startup.register(on_startup_notifications)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


