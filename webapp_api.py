# webapp_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.webapp.api import router
import os

from fastapi.staticfiles import StaticFiles

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
        "https://telegram.org"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp_api:app", host="0.0.0.0", port=8000, reload=True)


app.mount("/app", StaticFiles(directory="static", html=True), name="static")