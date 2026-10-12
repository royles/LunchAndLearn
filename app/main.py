from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Local LLM Chat", lifespan=lifespan)

app.include_router(api_router)


@app.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _mount_frontend() -> None:
    dist = settings.static_dir
    if not dist.is_dir():
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index_path = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def spa_index():
        if index_path.is_file():
            return FileResponse(index_path)
        return JSONResponse(
            {"detail": "Frontend not built. Run: cd frontend && npm ci && npm run build"},
            status_code=503,
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        blocked_prefixes = ("api/", "docs", "redoc", "openapi.json")
        if full_path.startswith(blocked_prefixes) or full_path == "healthcheck":
            raise HTTPException(status_code=404)
        candidate = dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        if index_path.is_file():
            return FileResponse(index_path)
        raise HTTPException(status_code=404)


_mount_frontend()
