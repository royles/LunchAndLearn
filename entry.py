"""Cloudera AI Workbench Application entrypoint."""

import uvicorn

from app.config import settings
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.resolve_port(),
        log_level="info",
    )
