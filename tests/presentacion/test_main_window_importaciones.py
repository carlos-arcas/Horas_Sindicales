from __future__ import annotations

import importlib
import inspect
import sys
import types

import pytest

MODULO_IMPORTACIONES = "app.ui.vistas.main_window.importaciones"


class _QtConst:
    def __getattr__(self, _name: str) -> int:
        return 0


class _QtDummyModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "Qt":
            return _QtConst()
        return type(name, (), {})


@pytest.fixture
def entorno_qt_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    pyside = types.ModuleType("PySide6")
    qt_widgets = _QtDummyModule("PySide6.QtWidgets")
    qt_core = _QtDummyModule("PySide6.QtCore")
    qt_gui = _QtDummyModule("PySide6.QtGui")
    qt_print = _QtDummyModule("PySide6.QtPrintSupport")
    qt_charts = _QtDummyModule("PySide6.QtCharts")

    qt_core.Signal = lambda *args, **kwargs: object()
    qt_core.Slot = lambda *args, **kwargs: (lambda fn: fn)

    pyside.QtWidgets = qt_widgets
    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtPrintSupport = qt_print
    pyside.QtCharts = qt_charts

    monkeypatch.setitem(sys.modules, "PySide6", pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qt_widgets)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)
    monkeypatch.setitem(sys.modules, "PySide6.QtGui", qt_gui)
    monkeypatch.setitem(sys.modules, "PySide6.QtPrintSupport", qt_print)
    monkeypatch.setitem(sys.modules, "PySide6.QtCharts", qt_charts)


@pytest.fixture
def importaciones(entorno_qt_stub: None) -> object:
    sys.modules.pop(MODULO_IMPORTACIONES, None)
    return importlib.import_module(MODULO_IMPORTACIONES)


def test_cargar_importacion_grupo_aplica_fallback_cuando_falta_qt(
    importaciones: object,
) -> None:
    def _carga_fallida() -> dict[str, object]:
        raise ImportError("No module named PySide6", name="PySide6")

    fallback = {"valor": object()}
    resultado = importaciones._cargar_importacion_grupo(  # type: ignore[attr-defined]
        _carga_fallida,
        fallback,
        nombre_grupo="acciones",
    )

    assert resultado is fallback


def test_cargar_importacion_grupo_no_oculta_error_no_qt(
    importaciones: object,
) -> None:
    def _carga_fallida() -> dict[str, object]:
        raise ImportError("fallo real de import", name="app.ui.modulo_roto")

    with pytest.raises(ImportError, match="fallo real de import"):
        importaciones._cargar_importacion_grupo(  # type: ignore[attr-defined]
            _carga_fallida,
            {"valor": object()},
            nombre_grupo="acciones",
        )


def test_cargar_importacion_grupo_falla_rapido_en_dependencias_criticas(
    importaciones: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _carga_fallida() -> dict[str, object]:
        raise ImportError("No module named PySide6", name="PySide6")

    caplog.set_level("ERROR")

    with pytest.raises(
        importaciones.ImportacionCriticaMainWindowError,  # type: ignore[attr-defined]
        match="grupo 'dialogos'",
    ):
        importaciones._cargar_importacion_grupo(  # type: ignore[attr-defined]
            _carga_fallida,
            {},
            nombre_grupo="dialogos",
            simbolos_criticos=("GestorToasts", "NotificationService"),
        )

    assert "MAINWINDOW_UI_CRITICAL_IMPORT_FAILED" in caplog.text
    assert any(
        getattr(registro, "extra", {}).get("simbolos_criticos")
        == ["GestorToasts", "NotificationService"]
        for registro in caplog.records
    )


def test_importaciones_segmenta_carga_por_responsabilidad(importaciones: object) -> None:
    for nombre_loader in (
        "_cargar_grupo_dialogos_y_controllers",
        "_cargar_grupo_acciones_y_estado",
        "_cargar_grupo_helpers_builders_y_sync",
    ):
        assert callable(getattr(importaciones, nombre_loader))


def test_importaciones_no_depende_de_globals_update_como_nucleo(
    importaciones: object,
) -> None:
    codigo = inspect.getsource(importaciones)

    assert "globals().update" not in codigo


def test_importaciones_expone_namespaces_y_compatibilidad_publica_minima(
    importaciones: object,
) -> None:
    assert hasattr(importaciones, "namespace_dialogos")
    assert hasattr(importaciones, "namespace_acciones")
    assert hasattr(importaciones, "namespace_helpers")
    assert importaciones.toast_error is importaciones.namespace_acciones.toast_error
    assert importaciones.status_badge is importaciones.namespace_helpers.status_badge
    assert (
        importaciones.run_init_refresh
        is importaciones.namespace_helpers.run_init_refresh
    )


def test_importaciones_limita_aliases_planos_legacy(importaciones: object) -> None:
    assert importaciones.__all__ == [
        "namespace_dialogos",
        "namespace_acciones",
        "namespace_helpers",
        "ImportacionCriticaMainWindowError",
        "SIMBOLOS_CRITICOS_POR_GRUPO",
        "GestorToasts",
        "PersonasController",
        "SolicitudesController",
        "SyncController",
        "PdfController",
        "NotificationService",
        "PushWorker",
        "SaldosCard",
        "MainWindowHealthMixin",
        "toast_error",
        "status_badge",
        "run_init_refresh",
    ]


def test_guardrail_criticos_no_tienen_fallbacks_peligrosos(importaciones: object) -> None:
    criticos = importaciones.SIMBOLOS_CRITICOS_POR_GRUPO  # type: ignore[attr-defined]
    fallback_dialogos = importaciones._FALLBACK_GRUPO_DIALOGOS  # type: ignore[attr-defined]
    fallback_helpers = importaciones._FALLBACK_GRUPO_HELPERS  # type: ignore[attr-defined]

    assert set(criticos["dialogos"]).isdisjoint(fallback_dialogos)
    assert set(criticos["helpers"]).isdisjoint(fallback_helpers)
