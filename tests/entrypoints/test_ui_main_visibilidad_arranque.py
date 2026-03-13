from __future__ import annotations

import sys
from types import SimpleNamespace

from app.entrypoints import ui_main


class _WindowSpy:
    def __init__(self, estado_inicial: int = 0) -> None:
        self.eventos: list[str] = []
        self._estado = estado_inicial

    def show(self) -> None:
        self.eventos.append("show")

    def showMaximized(self) -> None:
        self.eventos.append("showMaximized")

    def isMaximized(self) -> bool:
        self.eventos.append("isMaximized")
        return bool(self._estado == 2)

    def windowState(self) -> int:
        self.eventos.append("windowState")
        return self._estado

    def setWindowState(self, _valor) -> None:
        self.eventos.append("setWindowState")

    def raise_(self) -> None:
        self.eventos.append("raise")

    def activateWindow(self) -> None:
        self.eventos.append("activateWindow")



def test_activar_y_visibilizar_ventana_maximiza_sin_show(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "PySide6.QtCore",
        SimpleNamespace(Qt=SimpleNamespace(WindowState=SimpleNamespace(WindowNoState=0, WindowActive=8, WindowMaximized=2))),
    )
    monkeypatch.setattr(ui_main, "_es_objeto_qt_valido", lambda _obj: True)

    window = _WindowSpy(estado_inicial=0)
    coordinador = SimpleNamespace()

    ui_main._CoordinadorArranqueConCierreDeterminista._activar_y_visibilizar_ventana(
        coordinador,
        window,
        iniciar_maximizada=True,
    )

    assert "showMaximized" in window.eventos
    assert "show" not in window.eventos



def test_activar_y_visibilizar_ventana_no_fuerza_maximizado(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "PySide6.QtCore",
        SimpleNamespace(Qt=SimpleNamespace(WindowState=SimpleNamespace(WindowNoState=0, WindowActive=8, WindowMaximized=2))),
    )
    monkeypatch.setattr(ui_main, "_es_objeto_qt_valido", lambda _obj: True)

    window = _WindowSpy(estado_inicial=0)
    coordinador = SimpleNamespace()

    ui_main._CoordinadorArranqueConCierreDeterminista._activar_y_visibilizar_ventana(
        coordinador,
        window,
        iniciar_maximizada=False,
    )

    assert "show" in window.eventos
    assert "showMaximized" not in window.eventos



def test_activar_y_visibilizar_ventana_respeta_estado_maximizado_restaurado(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "PySide6.QtCore",
        SimpleNamespace(Qt=SimpleNamespace(WindowState=SimpleNamespace(WindowNoState=0, WindowActive=8, WindowMaximized=2))),
    )
    monkeypatch.setattr(ui_main, "_es_objeto_qt_valido", lambda _obj: True)

    window = _WindowSpy(estado_inicial=2)
    coordinador = SimpleNamespace()

    ui_main._CoordinadorArranqueConCierreDeterminista._activar_y_visibilizar_ventana(
        coordinador,
        window,
        iniciar_maximizada=False,
    )

    assert "showMaximized" in window.eventos
    assert "show" not in window.eventos



def test_crear_ventana_arranque_wizard_no_contamina_inicio_maximizado() -> None:
    wizard = object()
    orquestador = SimpleNamespace(
        resolver_onboarding=lambda: True,
        wizard_bienvenida=wizard,
        debe_iniciar_maximizada=lambda: True,
    )
    deps_arranque = SimpleNamespace(
        obtener_estado_onboarding=SimpleNamespace(ejecutar=lambda: False)
    )
    resolved_container = SimpleNamespace(
        repositorio_preferencias=None,
        cargar_datos_demo_caso_uso=None,
    )
    coordinador = SimpleNamespace(
        _marcar_boot_stage=lambda _stage: None,
        main_window_factory=lambda *_args, **_kwargs: object(),
        instalar_menu_ayuda=lambda *_args, **_kwargs: None,
        i18n=SimpleNamespace(),
    )

    ventana, iniciar_maximizada = ui_main._CoordinadorArranqueConCierreDeterminista._crear_ventana_arranque(
        coordinador,
        deps_arranque,
        orquestador,
        resolved_container,
    )

    assert ventana is wizard
    assert iniciar_maximizada is False
