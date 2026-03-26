from __future__ import annotations

from scripts import runtime_python


class _FakePath:
    def __init__(self, value: str, exists: bool) -> None:
        self.value = value
        self._exists = exists

    def exists(self) -> bool:
        return self._exists

    def __str__(self) -> str:
        return self.value


def test_resolve_repo_python_prefiere_dotvenv(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_python,
        "_venv_python_candidates",
        lambda: (
            _FakePath("D:/repo/.venv/Scripts/python.exe", True),
            _FakePath("D:/repo/.venv/bin/python", False),
        ),
    )
    monkeypatch.setattr(runtime_python.sys, "executable", "C:/Python313/python.exe")

    assert runtime_python.resolve_repo_python() == "D:/repo/.venv/Scripts/python.exe"


def test_resolve_repo_python_hace_fallback_al_interprete_actual(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_python,
        "_venv_python_candidates",
        lambda: (
            _FakePath("D:/repo/.venv/Scripts/python.exe", False),
            _FakePath("D:/repo/.venv/bin/python", False),
        ),
    )
    monkeypatch.setattr(runtime_python.sys, "executable", "C:/Python313/python.exe")

    assert runtime_python.resolve_repo_python() == "C:/Python313/python.exe"
