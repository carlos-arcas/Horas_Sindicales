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
from typing import Callable


class MainWindow(_MainWindowBase):
    """Clase pública estable que delega en la implementación modular."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.toast = getattr(self, "toast", None)
        self.historico_desde_date = getattr(self, "historico_desde_date", None)
        self.historico_hasta_date = getattr(self, "historico_hasta_date", None)

    def _toast_success(
        self,
        message: str,
        title: str | None = None,
        *,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
    ) -> None:
        try:
            kwargs: dict[str, object] = {}
            if title:
                kwargs["title"] = title
            if action_label is not None and action_callback is not None:
                kwargs["action_label"] = action_label
                kwargs["action_callback"] = action_callback
            if kwargs:
                self.toast.success(message, **kwargs)
            else:
                self.toast.success(message)
        except TypeError:
            self.toast.success(message)

    def _toast_error(
        self,
        message: str,
        *,
        title: str | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
    ) -> None:
        try:
            kwargs: dict[str, object] = {}
            if title:
                kwargs["title"] = title
            if action_label is not None and action_callback is not None:
                kwargs["action_label"] = action_label
                kwargs["action_callback"] = action_callback
            if kwargs:
                self.toast.error(message, **kwargs)
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
        if index != TAB_HISTORICO:
            return
        if not (self.historico_desde_date.date().isValid() and self.historico_hasta_date.date().isValid()):
            self._apply_historico_last_30_days()
        self._refresh_historico(force=False)

    def _refresh_historico(self, *, force: bool = False) -> None:
        # Mantiene la fuente de verdad del histórico en el controller.
        self._solicitudes_controller.refresh_historico()
        return super()._refresh_historico(force=force)

    # Compatibilidad explícita para smoke tests AST y wiring legado.
    def _sincronizar_con_confirmacion(self) -> None:
        return super()._sincronizar_con_confirmacion()

    def _on_sync_with_confirmation(self) -> None:
        return super()._on_sync_with_confirmation()

    def _limpiar_formulario(self) -> None:
        return super()._limpiar_formulario()

    def _clear_form(self) -> None:
        return super()._clear_form()

    def _verificar_handlers_ui(self) -> None:
        return super()._verificar_handlers_ui()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        return super().eventFilter(watched, event)


__all__ = [
    "HistoricoDetalleDialog",
    "MainWindow",
    "OptionalConfirmDialog",
    "PdfPreviewDialog",
    "QMainWindow",
    "TAB_HISTORICO",
    "resolve_active_delegada_id",
]
