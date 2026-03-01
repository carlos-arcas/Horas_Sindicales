import importlib


def test_repos_sqlite_module_import_smoke() -> None:
    module = importlib.import_module("app.infrastructure.repos_sqlite")

    assert module is not None
    assert hasattr(module, "PersonaRepositorySQLite")
