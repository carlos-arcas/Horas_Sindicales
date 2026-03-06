from __future__ import annotations

import logging

from app.ui.qt_compat import QLabel, QDate, QFrame, QSizePolicy, QTableView, QTimer, QVBoxLayout, QWidget
from app.ui.copy_catalog import copy_text
from app.ui.i18n_interfaz import cambiar_idioma_interfaz, texto_interfaz

from . import layout_builder, wiring
from .utilidades_controlador_estado import (
    apply_help_preferences,
    apply_solicitudes_tooltips,
    configure_historico_focus_order,
    configure_operativa_focus_order,
    configure_solicitudes_table,
    configure_time_placeholders,
    normalize_input_heights,
    on_help_toggle_changed,
    safe_conflicts_count,
    status_to_label,
    warmup_sync_client,
)
from app.ui.vistas.main_window.importaciones import run_init_refresh
from .contrato_botones import aplicar_contrato_botones_criticos_runtime

logger = logging.getLogger(__name__)


class InicializacionMainWindowMixin:
    def cambiar_idioma(self, idioma: str) -> None:
        cambiar_idioma_interfaz(idioma)

    def _refrescar_textos_sync(self) -> None:
        if hasattr(self, "sync_panel_status"):
            self.sync_panel_status.setText(texto_interfaz("ui.sync.panel.estado_pendiente"))
        if hasattr(self, "sync_status_label"):
            self.sync_status_label.setText(texto_interfaz("ui.sync.panel.sincronizando"))
        reminder = getattr(self, "conflicts_reminder_label", None)
        if reminder is not None and reminder.isVisible():
            reminder.setText(texto_interfaz("ui.sync.panel.conflictos_pendientes", cantidad=self._safe_conflicts_count()))

    def _safe_conflicts_count(self) -> int:
        return safe_conflicts_count(self)

    def _post_init_ui(self) -> None:
        main_tabs = getattr(self, "main_tabs", None)
        if main_tabs is None or not hasattr(main_tabs, "count") or main_tabs.count() >= 1:
            return
        fallback_page = getattr(self, "page_solicitudes", None) or QWidget(self)
        if not getattr(fallback_page, "objectName", lambda: "")():
            fallback_page.setObjectName("page_solicitudes_fallback")
        tab_text = fallback_page.windowTitle() if hasattr(fallback_page, "windowTitle") else ""
        if hasattr(main_tabs, "addTab") and hasattr(main_tabs, "indexOf") and main_tabs.indexOf(fallback_page) == -1:
            main_tabs.addTab(fallback_page, tab_text)

    def _inicializar_preferencia_pantalla_completa(self) -> None:
        if self.preferencia_pantalla_completa_check is None or self._obtener_preferencia_pantalla_completa is None:
            return
        preferencia = self._obtener_preferencia_pantalla_completa.ejecutar()
        self.preferencia_pantalla_completa_check.blockSignals(True)
        self.preferencia_pantalla_completa_check.setChecked(preferencia)
        self.preferencia_pantalla_completa_check.blockSignals(False)

    def _on_toggle_preferencia_pantalla_completa(self, valor: bool) -> None:
        if self._guardar_preferencia_pantalla_completa is not None:
            self._guardar_preferencia_pantalla_completa.ejecutar(valor)

    def _apply_help_preferences(self) -> None:
        apply_help_preferences(self)

    def _on_help_toggle_changed(self, enabled: bool) -> None:
        on_help_toggle_changed(self, enabled)

    def _apply_solicitudes_tooltips(self, enabled: bool | None = None) -> None:
        apply_solicitudes_tooltips(self, enabled)

    def _warmup_sync_client(self) -> None:
        warmup_sync_client(self, logger)

    def _post_init_load(self) -> None:
        run_init_refresh(
            refresh_resumen=self._refresh_saldos,
            refresh_pendientes=self._reload_pending_views,
            refresh_historico=lambda: self._refresh_historico(force=True),
            emit_log=logger.info,
        )
        QTimer.singleShot(0, self._warmup_sync_client)

    def _init_refresh(self) -> None:
        self._post_init_load()

    def _validate_required_widgets(self) -> None:
        required_widgets = (
            "persona_combo",
            "fecha_input",
            "desde_input",
            "hasta_input",
            "completo_check",
            "agregar_button",
            "pendientes_table",
            "main_tabs",
            "sync_source_label",
            "sync_scope_label",
            "sync_idempotency_label",
        )
        for widget_name in required_widgets:
            if not hasattr(self, widget_name):
                raise RuntimeError(f"{copy_text('ui.sync.mainwindow_incompleta')} {widget_name}")

    def _create_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)
        if title.strip():
            title_label = QLabel(title)
            title_label.setProperty("role", "cardTitle")
            card_layout.addWidget(title_label)
            separator = QFrame()
            separator.setProperty("role", "cardSeparator")
            separator.setFixedHeight(1)
            card_layout.addWidget(separator)
        return card, card_layout

    def _configure_disclosure(
        self,
        button,
        content,
        *,
        collapsed_text: str = copy_text("ui.sync.ver_detalles"),
        expanded_text: str = copy_text("ui.sync.ocultar_detalles"),
        expandido_por_defecto: bool = False,
    ) -> None:
        button.setCheckable(True)

        def _toggle(checked: bool) -> None:
            content.setVisible(checked)
            button.setText(expanded_text if checked else collapsed_text)

        button.toggled.connect(_toggle)
        _toggle(expandido_por_defecto)
        button.setChecked(expandido_por_defecto)

    def _build_ui(self) -> None:
        wiring.build_ui(self)
        aplicar_contrato_botones_criticos_runtime(self)
        self._update_conflicts_reminder()

    def _build_layout(self) -> None:
        layout_builder.build_layout_phase(self)

    def _wire_signals(self) -> None:
        wiring.wire_signals_phase(self)

    def _apply_initial_state(self) -> None:
        layout_builder.apply_initial_state_phase(self)

    def _create_widgets(self) -> None:
        layout_builder.create_widgets(self)

    def _build_shell_layout(self) -> None:
        layout_builder.build_shell(self)

    def _build_status_bar(self) -> None:
        layout_builder.build_status(self)

    def _configure_time_placeholders(self) -> None:
        configure_time_placeholders(self)

    def _normalize_input_heights(self) -> None:
        normalize_input_heights(self, logger)

    def _configure_operativa_focus_order(self) -> None:
        configure_operativa_focus_order(self)

    def _configure_historico_focus_order(self) -> None:
        configure_historico_focus_order(self, logger)

    def _status_to_label(self, status: str) -> str:
        return status_to_label(status)

    def _configure_solicitudes_table(self, table: QTableView) -> None:
        configure_solicitudes_table(table)

    def _on_fecha_changed(self, qdate: QDate) -> None:
        self._fecha_seleccionada = QDate(qdate) if hasattr(qdate, "isValid") and qdate.isValid() else None
        refrescar_operativa = getattr(self, "_refrescar_estado_operativa", None)
        if callable(refrescar_operativa):
            refrescar_operativa("fecha_changed")

    def _on_desde_changed(self, _qtime: object) -> None:
        refrescar_operativa = getattr(self, "_refrescar_estado_operativa", None)
        if callable(refrescar_operativa):
            refrescar_operativa("hora_desde_changed")

    def _on_hasta_changed(self, _qtime: object) -> None:
        refrescar_operativa = getattr(self, "_refrescar_estado_operativa", None)
        if callable(refrescar_operativa):
            refrescar_operativa("hora_hasta_changed")
