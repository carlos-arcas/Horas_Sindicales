from __future__ import annotations

from importlib import import_module

__all__ = [
    "MainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
    "QMainWindow",
    "HistoricoDetalleDialog",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
]

_EXPORTS_COMPAT = {
    "MainWindow": ("app.ui.vistas.main_window.state_controller", "MainWindow"),
    "TAB_HISTORICO": ("app.ui.vistas.main_window.navegacion_mixin", "TAB_HISTORICO"),
    "resolve_active_delegada_id": ("app.ui.vistas.main_window.state_helpers", "resolve_active_delegada_id"),
    "QMainWindow": ("app.ui.qt_compat", "QMainWindow"),
    "HistoricoDetalleDialog": ("app.ui.vistas.main_window.layout_builder", "HistoricoDetalleDialog"),
    "OptionalConfirmDialog": ("app.ui.vistas.main_window.layout_builder", "OptionalConfirmDialog"),
    "PdfPreviewDialog": ("app.ui.vistas.main_window.layout_builder", "PdfPreviewDialog"),
}


def __getattr__(nombre: str) -> object:
    """Shim de compatibilidad con carga diferida; usar submódulos explícitos internamente."""
    try:
        modulo_nombre, atributo = _EXPORTS_COMPAT[nombre]
    except KeyError as exc:
        raise AttributeError(nombre) from exc
    return getattr(import_module(modulo_nombre), atributo)
