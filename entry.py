"""Cloudera AI Workbench Application entrypoint."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


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


def ensure_frontend_built() -> None:
    """Build React assets when dist/ is missing (e.g. fresh clone on CML)."""
    if os.environ.get("SKIP_FRONTEND_BUILD", "").lower() in ("1", "true", "yes"):
        return
    if (FRONTEND_DIST / "index.html").is_file():
        return
    if not (FRONTEND_DIR / "package.json").is_file():
        print("No frontend/package.json; skipping UI build.", flush=True)
        return
    if not shutil.which("npm"):
        print(
            "npm not found; UI will show a build hint until frontend/dist exists.",
            flush=True,
        )
        return

    print("Building frontend (frontend/dist missing)…", flush=True)
    subprocess.check_call(["npm", "ci"], cwd=FRONTEND_DIR)
    subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND_DIR)


def main() -> None:
    ensure_dependencies()
    ensure_frontend_built()

    import uvicorn

    from app.config import settings
    from app.main import app

    dist = settings.static_dir.resolve()
    if (dist / "index.html").is_file():
        print(f"Serving UI from {dist}", flush=True)
    else:
        print(
            f"UI not found at {dist}; root URL will show build instructions.",
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
