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


def __getattr__(name: str):
    if name in {"HistoricoDetalleDialog", "OptionalConfirmDialog", "PdfPreviewDialog"}:
        module = import_module(".layout_builder", __name__)
    elif name in {"MainWindow", "QMainWindow", "TAB_HISTORICO", "resolve_active_delegada_id"}:
        module = import_module(".state_controller", __name__)
    else:
        raise AttributeError(name)

    value = getattr(module, name)
    globals()[name] = value
    return value
