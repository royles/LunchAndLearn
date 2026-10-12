"""Cloudera AI Workbench Application entrypoint."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _entry_project_root() -> Path:
    """Project root when this file is executed as a script or via IPython exec."""
    if globals().get("__file__"):
        return Path(__file__).resolve().parent
    # Deferred import: app.paths uses app/config package layout.
    root = Path.cwd()
    if (root / "app").is_dir() and (root / "requirements.txt").is_file():
        return root.resolve()
    for key in ("PROJECT_ROOT", "CDSW_PROJECT", "CDSW_WORKING_DIRECTORY"):
        raw = os.environ.get(key)
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_dir():
                return candidate.resolve()
    return root.resolve()


def _prepare_environment(project_root: Path) -> None:
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    os.chdir(project_root)


PROJECT_ROOT = _entry_project_root()
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
_prepare_environment(PROJECT_ROOT)


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


# Cloudera AI may execute this script inside IPython (Cell In[n]) without __file__.
if __name__ == "__main__":
    main()
else:
    # Application runner: exec entire file with __name__ != "__main__"
    if os.environ.get("CDSW_APP_PORT") or os.environ.get("CDSW_READONLY_PORT"):
        main()
