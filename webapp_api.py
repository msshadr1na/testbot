from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.webapp.api import router
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Fitness Bot Web App",
    description="API для мини-приложения Telegram",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://t.me",
        "https://telegram.org",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

def _read_static(filename: str) -> str:
    with open(STATIC_DIR / filename, encoding="utf-8") as f:
        return f.read()

@app.get("/orgs", response_class=HTMLResponse)
async def get_orgs_page():
    return HTMLResponse(content=_read_static("org_menu.html"))

@app.get("/worker", response_class=HTMLResponse)
async def get_orgs_page():
    return HTMLResponse(content=_read_static("worker_orgs.html"))

@app.get("/client", response_class=HTMLResponse)
async def get_orgs_page():
    return HTMLResponse(content=_read_static("client_orgs.html"))

@app.get("/client/history", response_class=HTMLResponse)
async def get_client_history_page():
    return RedirectResponse(url="/app/client_history.html", status_code=307)

@app.get("/client/schedule", response_class=HTMLResponse)
async def get_client_schedule_page():
    return RedirectResponse(url="/app/client_events.html", status_code=307)

@app.get("/client/html", response_class=HTMLResponse)
async def get_client_html_compat_page():
    return RedirectResponse(url="/app/client_history.html", status_code=307)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("webapp_api:app", host="0.0.0.0", port=8000, reload=True)

