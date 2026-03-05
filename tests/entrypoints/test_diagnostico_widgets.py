from __future__ import annotations

from app.entrypoints.diagnostico_widgets import (
    construir_info_top_level_widgets,
    hay_ventana_visible,
    seleccionar_ventana_principal,
)


class _WidgetStub:
    def __init__(
        self,
        *,
        object_name: str,
        window_title: str,
        visible: bool,
        hidden: bool,
        is_window: bool,
    ) -> None:
        self._object_name = object_name
        self._window_title = window_title
        self._visible = visible
        self._hidden = hidden
        self._is_window = is_window

    def objectName(self) -> str:
        return self._object_name

    def windowTitle(self) -> str:
        return self._window_title

    def isVisible(self) -> bool:
        return self._visible

    def isHidden(self) -> bool:
        return self._hidden

    def isWindow(self) -> bool:
        return self._is_window


def test_hay_ventana_visible_cubre_vacio_visible_y_no_visible() -> None:
    assert hay_ventana_visible([]) is False
    assert hay_ventana_visible([{"is_visible": True}]) is True
    assert (
        hay_ventana_visible([{"is_visible": False}, {"is_visible": False}]) is False
    )


def test_construir_info_top_level_widgets_genera_payload_esperado() -> None:
    widgets = [
        _WidgetStub(
            object_name="main_window",
            window_title="Horas Sindicales",
            visible=True,
            hidden=False,
            is_window=True,
        )
    ]

    payload = construir_info_top_level_widgets(widgets)

    assert payload == [
        {
            "clase": "_WidgetStub",
            "object_name": "main_window",
            "window_title": "Horas Sindicales",
            "is_visible": True,
            "is_hidden": False,
            "is_window": True,
        }
    ]


def test_seleccionar_ventana_principal_prioriza_mainwindow_visible() -> None:
    seleccionado = seleccionar_ventana_principal(
        [
            {"cls": "QWizard", "isVisible": True, "isWindow": True, "title": "Onboarding", "objectName": "wizard"},
            {"cls": "QMainWindow", "isVisible": True, "isWindow": True, "title": "Principal", "objectName": "main"},
        ]
    )

    assert seleccionado is not None
    assert seleccionado["candidato"]["cls"] == "QMainWindow"


def test_seleccionar_ventana_principal_elige_wizard_visible_si_no_hay_main() -> None:
    seleccionado = seleccionar_ventana_principal(
        [
            {"cls": "QWizard", "isVisible": True, "isWindow": True, "title": "Onboarding", "objectName": "wizard", "modal": True}
        ]
    )

    assert seleccionado is not None
    assert seleccionado["motivo"] == "wizard_visible"


def test_seleccionar_ventana_principal_devuelve_mainwindow_no_visible_como_candidata() -> None:
    seleccionado = seleccionar_ventana_principal(
        [
            {"cls": "QMainWindow", "isVisible": False, "isWindow": True, "title": "Principal", "objectName": "main"}
        ]
    )

    assert seleccionado is not None
    assert seleccionado["motivo"] == "main_window_no_visible"


def test_seleccionar_ventana_principal_descarta_solo_splash() -> None:
    assert (
        seleccionar_ventana_principal(
            [{"cls": "QSplashScreen", "isVisible": True, "isWindow": True, "title": "Cargando", "objectName": "splash"}]
        )
        is None
    )


def test_seleccionar_ventana_principal_ignora_fallback_visible() -> None:
    assert (
        seleccionar_ventana_principal(
            [{"cls": "QMainWindow", "isVisible": True, "isWindow": True, "title": "Fallback", "objectName": "fallback_window"}]
        )
        is None
    )


def test_seleccionar_ventana_principal_expone_score_y_motivo() -> None:
    seleccionado = seleccionar_ventana_principal(
        [
            {"cls": "QMainWindow", "isVisible": True, "isWindow": True, "title": "Principal", "objectName": "main"},
            {"cls": "QDialog", "isVisible": True, "isWindow": True, "title": "Onboarding", "objectName": "wizard", "modal": True},
        ]
    )

    assert seleccionado is not None
    assert seleccionado["score"] >= 90
    assert seleccionado["motivo"] == "main_window_visible"
