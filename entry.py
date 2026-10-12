"""Cloudera AI Workbench Application entrypoint."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"


def ensure_dependencies() -> None:
    """Install Python packages from requirements.txt before importing the app."""
    if os.environ.get("SKIP_DEPENDENCY_INSTALL", "").lower() in ("1", "true", "yes"):
        return
    if not REQUIREMENTS_FILE.is_file():
        return

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "-r",
        str(REQUIREMENTS_FILE),
    ]
    print(f"Installing dependencies from {REQUIREMENTS_FILE.name}…", flush=True)
    subprocess.check_call(cmd)


def main() -> None:
    ensure_dependencies()

    import uvicorn

    from app.config import settings
    from app.main import app

    dist = settings.static_dir.resolve()
    if (dist / "index.html").is_file():
        print(f"Serving UI from {dist}", flush=True)
    else:
        print(
            f"WARNING: UI not found at {dist}. "
            "Commit frontend/dist from a dev machine (see README).",
            flush=True,
        )

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.resolve_port(),
        log_level="info",
    )


if __name__ == "__main__":
    main()
