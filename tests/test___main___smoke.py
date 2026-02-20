from __future__ import annotations

import runpy

import pytest


def test_app_main_module_delegates_to_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr("app.entrypoints.main.main", lambda: 0)

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("app.__main__", run_name="__main__")

    assert exit_info.value.code == 0
