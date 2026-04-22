# webapp_api.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.webapp.api import router

app = FastAPI(
    title="Fitness Bot Web App",
    description="API для мини-приложения Telegram",
    version="0.1.0"
)

# Разрешить запросы из Telegram Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://t.me",
        "https://telegram.org",
        # Если ты открываешь в браузере напрямую с другого IP
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы из папки static
app.mount("/app", StaticFiles(directory="static", html=True), name="static")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp_api:app", host="0.0.0.0", port=8000, reload=True)