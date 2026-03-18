from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTimeEdit,
    QVBoxLayout,
)

from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.formulario_solicitud.bindings_senales import conectar_accion
from app.ui.vistas.builders.formulario_solicitud.contratos import TarjetaSeccion
from app.ui.vistas.builders.formulario_solicitud.ayudantes_qt import (
    configurar_altura_notas_compacta,
    crear_contenedor_hora,
    crear_placeholder_hora,
)

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def construir_tarjeta_solicitud(window: "MainWindow") -> TarjetaSeccion:
    solicitud_card, solicitud_layout = window._create_card("")
    solicitud_layout.setSpacing(8)
    _construir_banner_errores(window, solicitud_layout)
    _construir_datos_basicos(window, solicitud_layout)
    _construir_estado_formulario(window, solicitud_layout)
    solicitud_layout.addWidget(window.pending_errors_frame)
    return TarjetaSeccion(card=solicitud_card, layout=solicitud_layout)


def _construir_banner_errores(window: "MainWindow", layout: QVBoxLayout) -> None:
    window.pending_errors_frame = QFrame()
    window.pending_errors_frame.setProperty("role", "notice")
    pending_errors_layout = QVBoxLayout(window.pending_errors_frame)
    pending_errors_layout.setContentsMargins(10, 8, 10, 8)
    pending_errors_layout.setSpacing(6)
    window.pending_errors_title = QLabel(copy_text("solicitudes.pending_errors_title"))
    window.pending_errors_title.setProperty("role", "sectionTitle")
    pending_errors_layout.addWidget(window.pending_errors_title)
    window.pending_errors_summary = QLabel("")
    window.pending_errors_summary.setWordWrap(True)
    pending_errors_layout.addWidget(window.pending_errors_summary)
    window.goto_existing_button = QPushButton(copy_text("ui.solicitudes.ir_existente"))
    window.goto_existing_button.setProperty("variant", "ghost")
    conectar_accion(
        window, window.goto_existing_button.clicked, "_on_go_to_existing_duplicate"
    )
    window.goto_existing_button.setVisible(False)
    pending_errors_layout.addWidget(window.goto_existing_button)
    window.pending_errors_frame.setVisible(False)

    datos_basicos_label = QLabel(copy_text("solicitudes.form_section_title"))
    datos_basicos_label.setProperty("role", "sectionTitle")
    layout.addWidget(datos_basicos_label)


def _construir_datos_basicos(
    window: "MainWindow", solicitud_layout: QVBoxLayout
) -> None:
    _construir_fila_persona(window, solicitud_layout)
    _construir_fila_solicitud(window, solicitud_layout)
    _construir_fila_notas(window, solicitud_layout)
    _construir_fila_tips(window, solicitud_layout)


def _construir_fila_persona(
    window: "MainWindow", solicitud_layout: QVBoxLayout
) -> None:
    persona_row = QHBoxLayout()
    persona_row.setSpacing(10)
    persona_label = QLabel(copy_text("solicitudes.label_delegada"))
    persona_label.setProperty("role", "sectionTitle")
    persona_row.addWidget(persona_label)
    persona_row.addWidget(window.persona_combo, 1)
    solicitud_layout.addLayout(persona_row)


def _construir_fila_solicitud(
    window: "MainWindow", solicitud_layout: QVBoxLayout
) -> None:
    solicitud_row = QHBoxLayout()
    solicitud_row.setSpacing(10)
    solicitud_row.addWidget(QLabel(copy_text("solicitudes.label_fecha")))
    window.fecha_input = QDateEdit(QDate.currentDate())
    window.fecha_input.setCalendarPopup(True)
    solicitud_row.addWidget(window.fecha_input)

    _construir_controles_tramo(window, solicitud_row)
    _construir_controles_accion(window, solicitud_row)
    solicitud_row.addStretch(1)
    solicitud_layout.addLayout(solicitud_row)


def _construir_controles_tramo(
    window: "MainWindow", solicitud_row: QHBoxLayout
) -> None:
    window.desde_input = QTimeEdit(QTime(9, 0))
    window.desde_input.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
    window.desde_container = crear_contenedor_hora(
        "solicitudes.label_desde", window.desde_input
    )
    solicitud_row.addWidget(window.desde_container)
    window.desde_placeholder = crear_placeholder_hora()
    solicitud_row.addWidget(window.desde_placeholder)

    window.hasta_input = QTimeEdit(QTime(17, 0))
    window.hasta_input.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
    window.hasta_container = crear_contenedor_hora(
        "solicitudes.label_hasta", window.hasta_input
    )
    solicitud_row.addWidget(window.hasta_container)
    window.hasta_placeholder = crear_placeholder_hora()
    solicitud_row.addWidget(window.hasta_placeholder)


def _construir_controles_accion(
    window: "MainWindow", solicitud_row: QHBoxLayout
) -> None:
    window.completo_check = QCheckBox(copy_text("ui.solicitudes.completo"))
    solicitud_row.addWidget(window.completo_check)

    window.total_preview_label = QLabel(copy_text("ui.solicitudes.saldo_reservado"))
    window.total_preview_label.setProperty("role", "secondary")
    solicitud_row.addWidget(window.total_preview_label)

    window.total_preview_input = QLineEdit("00:00")
    window.total_preview_input.setReadOnly(True)
    window.total_preview_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.total_preview_input.setMaximumWidth(84)
    solicitud_row.addWidget(window.total_preview_input)

    window.cuadrante_warning_label = QLabel("")
    window.cuadrante_warning_label.setProperty("role", "secondary")
    window.cuadrante_warning_label.setVisible(False)
    solicitud_row.addWidget(window.cuadrante_warning_label)

    window.agregar_button = QPushButton(copy_text("solicitudes.button_add_pending"))
    window.agregar_button.setObjectName("agregar_button")
    window.agregar_button.setProperty("variant", "secondary")
    conectar_accion(window, window.agregar_button.clicked, "_on_add_pendiente")
    solicitud_row.addWidget(window.agregar_button)


def _construir_fila_notas(window: "MainWindow", solicitud_layout: QVBoxLayout) -> None:
    notas_row = QHBoxLayout()
    notas_row.setSpacing(8)
    notas_row.addWidget(QLabel(copy_text("solicitudes.label_notas")))
    window.notas_input = QPlainTextEdit()
    window.notas_input.setPlaceholderText(copy_text("solicitudes.placeholder_notas"))
    configurar_altura_notas_compacta(window.notas_input)
    _instalar_event_filters(window)
    window.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    notas_row.addWidget(window.notas_input, 1)
    solicitud_layout.addLayout(notas_row)


def _instalar_event_filters(window: "MainWindow") -> None:
    window.notas_input.installEventFilter(window)
    window.persona_combo.installEventFilter(window)
    window.fecha_input.installEventFilter(window)
    window.desde_input.installEventFilter(window)
    window.hasta_input.installEventFilter(window)
    window.completo_check.installEventFilter(window)


def _construir_fila_tips(window: "MainWindow", solicitud_layout: QVBoxLayout) -> None:
    tips_row = QHBoxLayout()
    tips_row.setSpacing(8)
    window.solicitudes_tip_1 = QLabel(copy_text("solicitudes.tip_enter"))
    window.solicitudes_tip_1.setProperty("role", "secondary")
    window.solicitudes_tip_2 = QLabel(copy_text("solicitudes.tip_minutes"))
    window.solicitudes_tip_2.setProperty("role", "secondary")
    window.solicitudes_tip_3 = QLabel(copy_text("solicitudes.tip_full_day"))
    window.solicitudes_tip_3.setProperty("role", "secondary")
    tips_row.addWidget(window.solicitudes_tip_1)
    tips_row.addWidget(window.solicitudes_tip_2)
    tips_row.addWidget(window.solicitudes_tip_3)
    tips_row.addStretch(1)
    solicitud_layout.addLayout(tips_row)


def _construir_estado_formulario(
    window: "MainWindow", solicitud_layout: QVBoxLayout
) -> None:
    status_row = QHBoxLayout()
    status_row.setSpacing(8)
    window.solicitudes_status_title = QLabel(copy_text("ui.solicitudes.estado"))
    window.solicitudes_status_title.setProperty("role", "sectionTitle")
    status_row.addWidget(window.solicitudes_status_title)
    window.solicitudes_status_label = QLabel(copy_text("solicitudes.status_ready"))
    window.solicitudes_status_label.setProperty("role", "secondary")
    status_row.addWidget(window.solicitudes_status_label)
    status_row.addSpacing(8)
    window.solicitudes_status_hint = QLabel("")
    window.solicitudes_status_hint.setProperty("role", "secondary")
    window.solicitudes_status_hint.setWordWrap(True)
    status_row.addWidget(window.solicitudes_status_hint, 1)
    solicitud_layout.addLayout(status_row)

    window.show_help_toggle = QCheckBox(copy_text("solicitudes.help_toggle"))
    window.show_help_toggle.setChecked(True)
    solicitud_layout.addWidget(window.show_help_toggle)

    _agregar_etiquetas_error(window, solicitud_layout)


def _agregar_etiquetas_error(
    window: "MainWindow", solicitud_layout: QVBoxLayout
) -> None:
    for atributo in (
        "solicitud_inline_error",
        "delegada_field_error",
        "fecha_field_error",
        "tramo_field_error",
    ):
        label = QLabel("")
        label.setProperty("role", "error")
        label.setVisible(False)
        setattr(window, atributo, label)
        solicitud_layout.addWidget(label)
