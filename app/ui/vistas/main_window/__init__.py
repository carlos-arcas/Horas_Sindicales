from __future__ import annotations

try:
    from .layout_builder import HistoricoDetalleDialog, OptionalConfirmDialog, PdfPreviewDialog
    from .state_controller import MainWindow, QMainWindow, TAB_HISTORICO, resolve_active_delegada_id
except Exception:  # pragma: no cover - fallback para entornos sin Qt runtime
    HistoricoDetalleDialog = object
    OptionalConfirmDialog = object
    PdfPreviewDialog = object
    MainWindow = object
    QMainWindow = object
    TAB_HISTORICO = 1

    def resolve_active_delegada_id(_delegada_ids: list[int], _preferred_id: object) -> int | None:
        return None


__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]
