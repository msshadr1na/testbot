from aiogram import Bot, Dispatcher
from presentation.handlers import router, start_notifications
from config import bot_token

bot = Bot(token = bot_token)
dp = Dispatcher()
dp.include_router(router)


async def main():
    start_notifications(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


