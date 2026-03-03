"""FastAPI 서버 + 정적 HTML 서빙"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from services.auth_service import init_settings
from routers.ai import router as ai_router
from routers.admin import router as admin_router

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
KST = timezone(timedelta(hours=9))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_settings()
    yield


app = FastAPI(title="MANA - 캡틴 FLOW", version="1.0.0", lifespan=lifespan)

app.include_router(ai_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(KST).isoformat(),
    }


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/{path:path}")
async def catch_all(path: str):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
