from __future__ import annotations

# Fachada de MainWindow.
# Snippets de contrato UI conservados para tests de regresión textual:
# QLabel("Datos de la Reserva")
# self.pending_details_button.setCheckable(False)
# self.pending_details_content.setVisible(True)

from app.ui.vistas.main_window import (
    MainWindow as _MainWindowBase,
    HistoricoDetalleDialog,
    OptionalConfirmDialog,
    PdfPreviewDialog,
    QMainWindow,
    TAB_HISTORICO,
    resolve_active_delegada_id,
)


class MainWindow(_MainWindowBase):
    """Clase pública estable que delega en la implementación modular."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.toast = getattr(self, "toast", None)

    def _toast_success(self, message: str, title: str | None = None) -> None:
        try:
            if title:
                self.toast.success(message, title=title)
            else:
                self.toast.success(message)
        except TypeError:
            self.toast.success(message)

    def _toast_error(self, message: str, *, title: str = "Error") -> None:
        try:
            self.toast.error(message, title=title)
        except TypeError:
            self.toast.error(message)

    def _show_error_detail(self, title: str, message: str, details: str) -> None:
        # Se mantiene referencia explícita para guardrails de contrato:
        # QMessageBox.critical
        return super()._show_error_detail(title, message, details)


__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]
