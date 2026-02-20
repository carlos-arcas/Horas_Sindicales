from __future__ import annotations

import os
import tempfile
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_log_dir() -> Path:
    candidates: list[Path] = []
    env_dir = os.environ.get("HORAS_LOG_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(project_root() / "logs")
    candidates.append(Path(tempfile.gettempdir()) / "HorasSindicales" / "logs")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / "_write_test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue

    fallback = project_root()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback
