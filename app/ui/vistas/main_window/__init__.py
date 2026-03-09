from __future__ import annotations

from app.ui.qt_compat import QMainWindow

from .layout_builder import HistoricoDetalleDialog, OptionalConfirmDialog, PdfPreviewDialog
from .navegacion_mixin import TAB_HISTORICO
from .state_helpers import resolve_active_delegada_id
from .state_controller import MainWindow

__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]
