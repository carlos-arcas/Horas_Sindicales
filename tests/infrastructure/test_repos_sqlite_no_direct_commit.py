from __future__ import annotations

from pathlib import Path


def test_repos_sqlite_no_usa_commit_directo() -> None:
    contenido = Path("app/infrastructure/repos_sqlite.py").read_text(encoding="utf-8")
    assert ".commit(" not in contenido
