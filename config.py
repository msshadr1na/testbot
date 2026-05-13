from dotenv import load_dotenv
import os

load_dotenv()

bot_token=os.getenv("BOT_TOKEN")

db_url=os.getenv("DB_URL")

# Базовый URL веб-приложения (без завершающего /). Для кнопок WebApp в Telegram.
web_app_base_url = (os.getenv("WEB_APP_BASE_URL") or "https://kilowatt-senorita-epidemic.ngrok-free.dev").rstrip("/")


