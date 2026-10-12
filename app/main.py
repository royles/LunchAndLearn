from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import settings
from app.db.session import init_db

_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Local LLM Chat</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0c0f14; color: #e8edf4;
           max-width: 40rem; margin: 4rem auto; padding: 0 1.5rem; line-height: 1.5; }
    code { background: #1c2430; padding: 0.15rem 0.4rem; border-radius: 4px; }
    a { color: #5b8cff; }
  </style>
</head>
<body>
  <h1>UI not built yet</h1>
  <p>The API is running, but the React frontend has not been built to
     <code>frontend/dist</code>.</p>
  <p>From the project root, run:</p>
  <pre><code>cd frontend && npm ci && npm run build</code></pre>
  <p>On Workbench, npm is usually unavailable — rebuild on a dev machine with
     <code>./scripts/build-frontend.sh</code> and push <code>frontend/dist</code> to git.</p>
  <p>API docs: <a href="/docs">/docs</a> · Health: <a href="/healthcheck">/healthcheck</a></p>
</body>
</html>"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Local LLM Chat", lifespan=lifespan)

app.include_router(api_router)


@app.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _index_path() -> Path:
    return settings.static_dir.resolve() / "index.html"


@app.get("/", include_in_schema=False)
async def spa_index():
    index_path = _index_path()
    if index_path.is_file():
        return FileResponse(index_path)
    return HTMLResponse(_FALLBACK_HTML, status_code=503)


def _mount_frontend() -> None:
    dist = settings.static_dir.resolve()
    index_path = dist / "index.html"
    if not index_path.is_file():
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        blocked = ("api", "docs", "redoc", "openapi.json", "healthcheck", "assets")
        first = full_path.split("/", 1)[0] if full_path else ""
        if first in blocked:
            raise HTTPException(status_code=404)
        candidate = dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_path)


_mount_frontend()
