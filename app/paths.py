"""Project root resolution (Cloudera may run entry.py in IPython without __file__)."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_project_root() -> Path:
    """
    Directory containing entry.py, requirements.txt, and app/.

    Used when the application script is executed via IPython (no __file__ on entry).
    """
    for key in ("PROJECT_ROOT", "CDSW_PROJECT", "CDSW_WORKING_DIRECTORY"):
        raw = os.environ.get(key)
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_dir():
                return candidate.resolve()

    cwd = Path.cwd()
    if (cwd / "app").is_dir() and (cwd / "requirements.txt").is_file():
        return cwd.resolve()
    if (cwd.parent / "app").is_dir() and (cwd.parent / "requirements.txt").is_file():
        return cwd.parent.resolve()

    # Package file is always present when app is importable.
    return Path(__file__).resolve().parents[1]
