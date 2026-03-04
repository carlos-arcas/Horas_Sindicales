from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QTreeWidget, QVBoxLayout, QWidget

from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.sync_panel.ayudantes_puros import claves_columnas_salud
from app.ui.vistas.builders.sync_panel.ayudantes_qt import crear_boton_accion, crear_label_secundario

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def construir_seccion_diagnostico(window: "MainWindow", sync_tab_layout: QVBoxLayout) -> None:
    diagnostics_card, diagnostics_layout = window._create_card(copy_text("ui.sync.panel_avanzado"))
    window.sync_diagnostics_button = QToolButton()
    window.sync_diagnostics_button.setText(copy_text("ui.sync.detalles_tecnicos"))
    window.sync_diagnostics_button.setCheckable(True)
    window.sync_diagnostics_button.setChecked(False)
    window.sync_diagnostics_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    diagnostics_layout.addWidget(window.sync_diagnostics_button, alignment=Qt.AlignLeft)

    window.sync_diagnostics_content = QWidget()
    window.sync_diagnostics_content.setVisible(False)
    content_layout = QVBoxLayout(window.sync_diagnostics_content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(8)
    _construir_items_diagnostico(window, content_layout)

    diagnostics_card.layout().addWidget(window.sync_diagnostics_content)
    sync_tab_layout.addWidget(diagnostics_card)


def _construir_items_diagnostico(window: "MainWindow", content_layout: QVBoxLayout) -> None:
    window.sync_details_button = crear_boton_accion(window, "ui.sync.ver_detalles", "secondary", "_on_show_sync_details", habilitado=False)
    window.copy_sync_report_button = crear_boton_accion(window, "ui.sync.copiar_informe", "secondary", "_on_copy_sync_report", habilitado=False)
    window.open_sync_logs_button = crear_boton_accion(window, "ui.sync.abrir_logs", "secondary", "_on_open_sync_logs")
    window.sync_history_button = crear_boton_accion(window, "ui.sync.ver_historial", "secondary", "_on_show_sync_history")

    content_layout.addWidget(window.sync_source_label)
    content_layout.addWidget(window.sync_scope_label)
    content_layout.addWidget(window.sync_idempotency_label)
    content_layout.addWidget(window.sync_trend_label)
    content_layout.addWidget(window.sync_details_button)
    content_layout.addWidget(window.copy_sync_report_button)
    content_layout.addWidget(window.open_sync_logs_button)
    content_layout.addWidget(window.sync_history_button)
    content_layout.addWidget(_crear_salud_sistema(window))


def _crear_salud_sistema(window: "MainWindow") -> QWidget:
    health_card, health_layout = window._create_card(copy_text("ui.sync.salud_sistema"))
    window.health_summary_label = crear_label_secundario("ui.sync.estado_general_pendiente")
    health_layout.addWidget(window.health_summary_label)

    window.health_checks_tree = QTreeWidget()
    window.health_checks_tree.setColumnCount(4)
    window.health_checks_tree.setHeaderLabels([copy_text(clave) for clave in claves_columnas_salud()])
    window.health_checks_tree.setMinimumHeight(180)
    health_layout.addWidget(window.health_checks_tree)

    actions = QHBoxLayout()
    window.refresh_health_button = crear_boton_accion(window, "ui.sync.actualizar_salud", "secondary", "_refresh_health_and_alerts")
    actions.addWidget(window.refresh_health_button)
    window.snooze_alerts_button = crear_boton_accion(window, "ui.sync.no_mostrar_hoy", "secondary", "_on_snooze_alerts_today")
    actions.addWidget(window.snooze_alerts_button)
    actions.addStretch(1)
    health_layout.addLayout(actions)
    return health_card
