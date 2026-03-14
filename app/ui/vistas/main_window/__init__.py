from __future__ import annotations

from importlib import import_module

__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]


def __getattr__(nombre: str) -> object:
    """Carga diferida para evitar imports Qt al usar submódulos puros."""

    if nombre == "QMainWindow":
        return import_module("app.ui.qt_compat").QMainWindow
    if nombre in {"HistoricoDetalleDialog", "OptionalConfirmDialog", "PdfPreviewDialog"}:
        modulo = import_module("app.ui.vistas.main_window.layout_builder")
        return getattr(modulo, nombre)
    if nombre == "TAB_HISTORICO":
        return import_module("app.ui.vistas.main_window.navegacion_mixin").TAB_HISTORICO
    if nombre == "resolve_active_delegada_id":
        modulo = import_module("app.ui.vistas.main_window.state_helpers")
        return modulo.resolve_active_delegada_id
    if nombre == "MainWindow":
        return import_module("app.ui.vistas.main_window.state_controller").MainWindow
    raise AttributeError(nombre)
