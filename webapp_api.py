from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.webapp.api import router
from fastapi.responses import HTMLResponse

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

app.mount("/app", StaticFiles(directory="static", html=True), name="static")

@app.get("/orgs", response_class=HTMLResponse)
async def get_orgs_page():
    with open("static/org_orgs.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp_api:app", host="0.0.0.0", port=8000, reload=True)

