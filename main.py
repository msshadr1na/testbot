from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from presentation.handlers import router
from config import bot_token

bot = Bot(token = bot_token)
dp = Dispatcher()
dp.include_router(router)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


