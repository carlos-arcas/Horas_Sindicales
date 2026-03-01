from __future__ import annotations

from app.entrypoints.ui_main import mostrar_main_window


class _WindowSpy:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def show(self) -> None:
        self.calls.append("show")

    def showMaximized(self) -> None:
        self.calls.append("showMaximized")


def test_mostrar_main_window_maximizada_si_preferencia_true() -> None:
    window = _WindowSpy()

    mostrar_main_window(window, iniciar_maximizada=True)

    assert window.calls == ["showMaximized"]


def test_mostrar_main_window_normal_si_preferencia_false() -> None:
    window = _WindowSpy()

    mostrar_main_window(window, iniciar_maximizada=False)

    assert window.calls == ["show"]
