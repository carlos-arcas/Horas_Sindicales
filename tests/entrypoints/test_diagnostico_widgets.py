from __future__ import annotations

from app.entrypoints.diagnostico_widgets import (
    construir_info_top_level_widgets,
    debe_abortar_watchdog_por_ventana_visible,
    decidir_cerrar_splash,
    es_widget_splash,
    hay_ventana_visible,
    hay_ventana_visible_no_splash,
    seleccionar_ventana_principal,
    validar_ventana_creada,
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


def test_hay_ventana_visible_no_splash_devuelve_false_si_solo_hay_splash() -> None:
    assert (
        hay_ventana_visible_no_splash(
            [{"clase": "SplashWindow", "is_visible": True, "object_name": "splash"}]
        )
        is False
    )


def test_es_widget_splash_detecta_por_clase() -> None:
    assert es_widget_splash({"clase": "SplashWindow", "object_name": "principal"}) is True
    assert es_widget_splash({"clase": "QSplashScreen", "object_name": "principal"}) is True


def test_es_widget_splash_detecta_por_object_name_normalizado() -> None:
    assert es_widget_splash({"clase": "QWidget", "object_name": " splash_window "}) is True
    assert es_widget_splash({"clase": "QWidget", "object_name": "MainWindow"}) is False


def test_hay_ventana_visible_no_splash_devuelve_true_con_splash_y_main() -> None:
    assert (
        hay_ventana_visible_no_splash(
            [
                {"clase": "SplashWindow", "is_visible": True, "object_name": "splash"},
                {"clase": "QMainWindow", "is_visible": True, "object_name": "main_window"},
            ]
        )
        is True
    )


def test_hay_ventana_visible_no_splash_ignora_fallback_visible() -> None:
    assert (
        hay_ventana_visible_no_splash(
            [
                {
                    "clase": "RecuperacionArranqueDialog",
                    "is_visible": True,
                    "object_name": "fallback_window",
                }
            ]
        )
        is False
    )


def test_debe_abortar_watchdog_por_ventana_visible_no_aborta_si_solo_hay_splash() -> None:
    hay_visible_no_splash = hay_ventana_visible_no_splash(
        [{"clase": "QSplashScreen", "is_visible": True, "object_name": "splash"}]
    )

    assert debe_abortar_watchdog_por_ventana_visible(hay_visible_no_splash) is False


def test_validar_ventana_creada_lanza_si_recibe_none() -> None:
    try:
        validar_ventana_creada(None)
    except RuntimeError as error:
        assert str(error) == "VENTANA_ARRANQUE_NO_CREADA"
    else:
        raise AssertionError("Se esperaba RuntimeError cuando la ventana es None")


def test_validar_ventana_creada_no_lanza_si_hay_instancia() -> None:
    validar_ventana_creada(object())


def test_decidir_cerrar_splash_retorna_true_solo_con_fallback() -> None:
    assert decidir_cerrar_splash(al_mostrar_fallback=True) is True
    assert decidir_cerrar_splash(al_mostrar_fallback=False) is False
