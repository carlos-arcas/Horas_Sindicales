from __future__ import annotations

import ast
from pathlib import Path


REPOS_SQLITE_PATH = Path("app/infrastructure/repos_sqlite.py")


def test_repos_sqlite_no_longer_contains_persona_repository_class() -> None:
    module = ast.parse(REPOS_SQLITE_PATH.read_text(encoding="utf-8"))

    class_names = {
        node.name
        for node in module.body
        if isinstance(node, ast.ClassDef)
    }

    assert "RepositorioPersonasSQLite" not in class_names
