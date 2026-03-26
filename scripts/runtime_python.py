from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _venv_python_candidates() -> tuple[Path, Path]:
    return (
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    )


def resolve_repo_python() -> str:
    for candidate in _venv_python_candidates():
        if candidate.exists():
            return str(candidate)
    return sys.executable
