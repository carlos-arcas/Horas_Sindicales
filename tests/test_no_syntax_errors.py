from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = ("app", "scripts", "tests")
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "caches",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


@pytest.mark.headless_safe
def test_no_python_syntax_errors_in_repo() -> None:
    syntax_errors: list[str] = []

    for relative_dir in TARGET_DIRS:
        base_dir = ROOT / relative_dir
        if not base_dir.exists():
            continue

        for current_root, dir_names, file_names in os.walk(base_dir):
            dir_names[:] = [name for name in dir_names if name not in EXCLUDED_DIRS]

            for file_name in file_names:
                if not file_name.endswith(".py"):
                    continue

                file_path = Path(current_root) / file_name
                try:
                    source = file_path.read_text(encoding="utf-8")
                    ast.parse(source, filename=str(file_path))
                except SyntaxError as exc:
                    line = exc.lineno or 0
                    column = exc.offset or 0
                    message = exc.msg or "SyntaxError"
                    relative_path = file_path.relative_to(ROOT)
                    syntax_errors.append(
                        f"{relative_path}:{line}:{column} -> {message}"
                    )

    if syntax_errors:
        pytest.fail(
            "Se detectaron errores de sintaxis en archivos Python:\n"
            + "\n".join(sorted(syntax_errors))
        )
