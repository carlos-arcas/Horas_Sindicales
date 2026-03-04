from __future__ import annotations

import logging

from app.ui.qt_compat import QEvent, QKeyEvent, QObject, Qt, QTimer

from .header_state import resolve_section_title, resolve_sidebar_tab_index
from .utilidades_controlador_estado import (
    update_responsive_columns,
    update_conflicts_reminder,
)

logger = logging.getLogger(__name__)
TAB_HISTORICO = 1


class NavegacionMainWindowMixin:
    def _sync_source_text(self) -> str:
        from . import acciones_sincronizacion

        return acciones_sincronizacion.sync_source_text(self)

    def _sync_scope_text(self) -> str:
        from . import acciones_sincronizacion

        return acciones_sincronizacion.sync_scope_text()

    def _sync_actor_text(self) -> str:
        from . import acciones_sincronizacion

        return acciones_sincronizacion.sync_actor_text(self)

    def _update_conflicts_reminder(self) -> None:
        update_conflicts_reminder(self, logger)

    def _on_main_tab_changed(self, index: int) -> None:
        if index != TAB_HISTORICO:
            return
        if not (
            self.historico_desde_date.date().isValid()
            and self.historico_hasta_date.date().isValid()
        ):
            self._apply_historico_last_30_days()
        self._refresh_historico(force=False)

    def _switch_sidebar_page(self, index: int) -> None:
        target_tab_index = index
        if self.main_tabs is not None and not (
            0 <= target_tab_index < self.main_tabs.count()
        ):
            mapped_tab_index = resolve_sidebar_tab_index(index)
            if mapped_tab_index is None and index != 0:
                return
            target_tab_index = mapped_tab_index

        self._active_sidebar_index = index
        if (
            self.main_tabs is not None
            and target_tab_index is not None
            and self.main_tabs.currentIndex() != target_tab_index
        ):
            self.main_tabs.setCurrentIndex(target_tab_index)
        self._refresh_header_title()

    def _refresh_header_title(self) -> None:
        header_title = getattr(self, "header_title_label", None)
        if header_title is None:
            return
        title = resolve_section_title(self._active_sidebar_index)
        if header_title.text() == title:
            return
        header_title.setText(title)

    def _update_responsive_columns(self) -> None:
        update_responsive_columns(self, logger)

    def ir_a_pendiente_existente(self, solicitud_id: int) -> None:
        try:
            if self.main_tabs is not None and self.main_tabs.currentIndex() != 0:
                self.main_tabs.setCurrentIndex(0)
            if (
                getattr(self, "ver_todas_pendientes_button", None) is not None
                and not self._pending_view_all
            ):
                self.ver_todas_pendientes_button.setChecked(True)
            if self._pending_view_all:
                self._reload_pending_views()
            if not self._focus_pending_by_id(solicitud_id):
                logger.warning(
                    "pending_row_not_found", extra={"solicitud_id": solicitud_id}
                )
                return
            pendientes_table = getattr(self, "pendientes_table", None)
            if pendientes_table is None:
                logger.warning(
                    "pending_table_missing", extra={"solicitud_id": solicitud_id}
                )
                return
            QTimer.singleShot(2500, pendientes_table.clearSelection)
        except Exception:
            logger.warning(
                "navigate_to_existing_pending_failed",
                extra={"solicitud_id": solicitud_id},
                exc_info=True,
            )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_responsive_columns()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        try:
            if watched is None or event is None:
                return False
            submit_widgets = {
                getattr(self, "persona_combo", None),
                getattr(self, "fecha_input", None),
                getattr(self, "desde_input", None),
                getattr(self, "hasta_input", None),
                getattr(self, "completo_check", None),
                getattr(self, "notas_input", None),
            }
            if (
                watched in submit_widgets
                and event.type() == QEvent.KeyPress
                and isinstance(event, QKeyEvent)
            ):
                key_getter = getattr(event, "key", None)
                modifiers_getter = getattr(event, "modifiers", None)
                if not callable(key_getter):
                    return super().eventFilter(watched, event)
                key = key_getter()
                modifiers = (
                    modifiers_getter() if callable(modifiers_getter) else Qt.NoModifier
                )
                if key in (Qt.Key_Return, Qt.Key_Enter) and modifiers == Qt.NoModifier:
                    logger.info("ENTER form detected via eventFilter")
                    self._dump_estado_pendientes("enter_form")
                    if self.agregar_button.isEnabled():
                        self.agregar_button.click()
                    else:
                        logger.info(
                            "eventFilter early_return motivo=agregar_button_disabled"
                        )
                    return True
            return super().eventFilter(watched, event)
        except Exception:
            logger.exception(
                "event_filter_failed",
                extra={
                    "watched": type(watched).__name__,
                    "event_type": type(event).__name__,
                },
            )
            return False
