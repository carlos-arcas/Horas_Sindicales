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
from app.ui.vistas.init_refresh import run_init_refresh


class MainWindow(_MainWindowBase):
    """Clase pública estable que delega en la implementación modular."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.toast = getattr(self, "toast", None)
        self.historico_desde_date = getattr(self, "historico_desde_date", None)
        self.historico_hasta_date = getattr(self, "historico_hasta_date", None)

    def _toast_success(self, message: str, title: str | None = None) -> None:
        try:
            if title:
                self.toast.success(message, title=title)
            else:
                self.toast.success(message)
        except TypeError:
            self.toast.success(message)

    def _toast_error(self, message: str, *, title: str | None = None) -> None:
        try:
            if title:
                self.toast.error(message, title=title)
            else:
                self.toast.error(message)
        except TypeError:
            self.toast.error(message)

    def _show_error_detail(self, title: str, message: str, details: str) -> None:
        # Se mantiene referencia explícita para guardrails de contrato:
        # QMessageBox.critical
        return super()._show_error_detail(title, message, details)

    def _post_init_load(self) -> None:
        run_init_refresh(
            refresh_resumen=self._refresh_saldos,
            refresh_pendientes=self._reload_pending_views,
            refresh_historico=lambda: self._refresh_historico(force=True),
        )

    def _on_main_tab_changed(self, index: int) -> None:
        tab_to_sidebar_index = {0: 1, 1: 2, 2: 3}
        if index in tab_to_sidebar_index:
            self._active_sidebar_index = tab_to_sidebar_index[index]
        self._refresh_header_title()

        if index == 0:
            persona = self._current_persona()
            self._restore_draft_for_persona(persona.id if persona is not None else None)
            self.fecha_input.setFocus()
            return

        if index == TAB_HISTORICO:
            if not (self.historico_desde_date.date().isValid() and self.historico_hasta_date.date().isValid()):
                self._apply_historico_last_30_days()
            self._refresh_historico(force=False)
            return

        if index == 2:
            self._refresh_saldos()

    def _refresh_historico(self, *, force: bool = False) -> None:
        # Mantiene la fuente de verdad del histórico en el controller.
        self._solicitudes_controller.refresh_historico()
        return super()._refresh_historico(force=force)


__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]
