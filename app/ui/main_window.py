from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, QTime, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_utils import minutes_to_hhmm
from app.ui.group_dialog import GrupoConfigDialog
from app.ui.models_qt import SolicitudesTableModel
from app.ui.person_dialog import PersonaDialog
from app.ui.style import apply_theme
from app.ui.widgets.header import HeaderWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        persona_use_cases: PersonaUseCases,
        solicitud_use_cases: SolicitudUseCases,
        grupo_use_cases: GrupoConfigUseCases,
    ) -> None:
        super().__init__()
        app = QApplication.instance()
        if app:
            apply_theme(app)
        self._persona_use_cases = persona_use_cases
        self._solicitud_use_cases = solicitud_use_cases
        self._grupo_use_cases = grupo_use_cases
        self._personas: list[PersonaDTO] = []
        self._pending_solicitudes: list[SolicitudDTO] = []
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self._load_personas()

    def _create_card(self, title: str, *, variant: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", True)
        if variant:
            card.setProperty("variant", variant)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setProperty("role", "cardTitle")
        card_layout.addWidget(title_label)

        separator = QFrame()
        separator.setProperty("role", "cardSeparator")
        separator.setFixedHeight(1)
        card_layout.addWidget(separator)

        return card, card_layout

    def _build_ui(self) -> None:
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header_frame = QFrame()
        header_frame.setProperty("role", "header")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header = HeaderWidget()
        header_layout.addWidget(header)
        header_separator = QFrame()
        header_separator.setObjectName("headerSeparator")
        header_separator.setFixedHeight(3)
        header_layout.addWidget(header_separator)
        layout.addWidget(header_frame)

        self._content_row = QBoxLayout(QBoxLayout.LeftToRight)
        self._content_row.setSpacing(16)
        layout.addLayout(self._content_row, 1)

        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        self._content_row.addLayout(left_column, 3)

        persona_card, persona_layout = self._create_card("Delegado")

        self.persona_combo = QComboBox()
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        persona_layout.addWidget(self.persona_combo)

        persona_actions = QHBoxLayout()
        persona_actions.setSpacing(8)
        self.add_persona_button = QPushButton("Nuevo delegado")
        self.add_persona_button.setProperty("variant", "secondary")
        self.add_persona_button.clicked.connect(self._on_add_persona)
        persona_actions.addWidget(self.add_persona_button)

        self.edit_persona_button = QPushButton("Editar delegado")
        self.edit_persona_button.setProperty("variant", "secondary")
        self.edit_persona_button.clicked.connect(self._on_edit_persona)
        persona_actions.addWidget(self.edit_persona_button)

        self.edit_grupo_button = QPushButton("Editar grupo")
        self.edit_grupo_button.setProperty("variant", "secondary")
        self.edit_grupo_button.clicked.connect(self._on_edit_grupo)
        persona_actions.addWidget(self.edit_grupo_button)
        persona_layout.addLayout(persona_actions)

        delete_row = QHBoxLayout()
        self.delete_persona_button = QPushButton("Eliminar delegado")
        self.delete_persona_button.setProperty("variant", "danger")
        self.delete_persona_button.clicked.connect(self._on_delete_persona)
        delete_row.addWidget(self.delete_persona_button)
        delete_row.addStretch(1)
        persona_layout.addLayout(delete_row)

        left_column.addWidget(persona_card)

        solicitud_card, solicitud_layout = self._create_card("Alta de solicitud")

        solicitud_row = QHBoxLayout()
        solicitud_row.setSpacing(10)

        solicitud_row.addWidget(QLabel("Fecha"))
        self.fecha_input = QDateEdit(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.dateChanged.connect(self._on_fecha_changed)
        solicitud_row.addWidget(self.fecha_input)

        self.desde_input = QTimeEdit(QTime(9, 0))
        self.desde_input.setDisplayFormat("HH:mm")
        self.desde_input.timeChanged.connect(self._update_solicitud_preview)
        self.desde_container = QWidget()
        desde_layout = QHBoxLayout(self.desde_container)
        desde_layout.setContentsMargins(0, 0, 0, 0)
        desde_layout.setSpacing(6)
        desde_layout.addWidget(QLabel("Desde"))
        desde_layout.addWidget(self.desde_input)
        solicitud_row.addWidget(self.desde_container)

        self.desde_placeholder = QWidget()
        self.desde_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        solicitud_row.addWidget(self.desde_placeholder)

        self.hasta_input = QTimeEdit(QTime(17, 0))
        self.hasta_input.setDisplayFormat("HH:mm")
        self.hasta_input.timeChanged.connect(self._update_solicitud_preview)
        self.hasta_container = QWidget()
        hasta_layout = QHBoxLayout(self.hasta_container)
        hasta_layout.setContentsMargins(0, 0, 0, 0)
        hasta_layout.setSpacing(6)
        hasta_layout.addWidget(QLabel("Hasta"))
        hasta_layout.addWidget(self.hasta_input)
        solicitud_row.addWidget(self.hasta_container)

        self.hasta_placeholder = QWidget()
        self.hasta_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        solicitud_row.addWidget(self.hasta_placeholder)

        self.completo_check = QCheckBox("Completo")
        self.completo_check.toggled.connect(self._on_completo_changed)
        solicitud_row.addWidget(self.completo_check)

        self.total_preview_label = QLabel("Total: 00:00")
        self.total_preview_label.setProperty("role", "secondary")
        solicitud_row.addWidget(self.total_preview_label)

        self.cuadrante_warning_label = QLabel("")
        self.cuadrante_warning_label.setProperty("role", "secondary")
        self.cuadrante_warning_label.setVisible(False)
        solicitud_row.addWidget(self.cuadrante_warning_label)

        self.agregar_button = QPushButton("Agregar")
        self.agregar_button.setProperty("variant", "primary")
        self.agregar_button.clicked.connect(self._on_add_pendiente)
        solicitud_row.addWidget(self.agregar_button)
        solicitud_row.addStretch(1)
        solicitud_layout.addLayout(solicitud_row)

        notas_row = QHBoxLayout()
        notas_row.setSpacing(8)
        notas_row.addWidget(QLabel("Notas"))
        self.notas_input = QPlainTextEdit()
        self.notas_input.setPlaceholderText("Notas para la solicitud")
        self.notas_input.setMinimumHeight(96)
        self.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        notas_row.addWidget(self.notas_input, 1)
        solicitud_layout.addLayout(notas_row)

        left_column.addWidget(solicitud_card)

        pendientes_card, pendientes_layout = self._create_card("Pendientes de confirmar", variant="key")
        pendientes_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pendientes_group = pendientes_card

        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pendientes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pendientes_table.setShowGrid(False)
        self.pendientes_table.setAlternatingRowColors(True)
        self.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pendientes_table.setMinimumHeight(220)
        self._configure_solicitudes_table(self.pendientes_table)
        pendientes_layout.addWidget(self.pendientes_table, 1)

        footer_separator = QFrame()
        footer_separator.setProperty("role", "footerSeparator")
        footer_separator.setFixedHeight(1)
        pendientes_layout.addWidget(footer_separator)

        pendientes_footer = QHBoxLayout()
        pendientes_footer.setSpacing(10)

        left_actions = QHBoxLayout()
        left_actions.setSpacing(8)
        self.eliminar_pendiente_button = QPushButton("Eliminar seleccionado")
        self.eliminar_pendiente_button.setProperty("variant", "danger")
        self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
        left_actions.addWidget(self.eliminar_pendiente_button)

        self.editar_pdf_button = QPushButton("Editar PDF")
        self.editar_pdf_button.setProperty("variant", "secondary")
        self.editar_pdf_button.clicked.connect(self._on_edit_pdf)
        left_actions.addWidget(self.editar_pdf_button)
        pendientes_footer.addLayout(left_actions)

        pendientes_footer.addStretch(1)
        self.abrir_pdf_check = QCheckBox("Abrir PDF al finalizar")
        self.abrir_pdf_check.setChecked(True)
        pendientes_footer.addWidget(self.abrir_pdf_check, 0, Qt.AlignCenter)

        pendientes_footer.addStretch(1)
        self.confirmar_button = QPushButton("Confirmar y Generar PDF")
        self.confirmar_button.setProperty("variant", "primary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        pendientes_footer.addWidget(self.confirmar_button, 0, Qt.AlignRight)

        pendientes_layout.addLayout(pendientes_footer)
        left_column.addWidget(pendientes_card, 1)

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        self._content_row.addLayout(right_column, 2)

        saldos_card, saldos_layout = self._create_card("Resumen de saldos")
        saldos_grid = QGridLayout()
        saldos_grid.setHorizontalSpacing(10)
        saldos_grid.setVerticalSpacing(8)

        saldos_grid.addWidget(QLabel(""), 0, 0)
        consumidas_header = QLabel("Consumidas")
        consumidas_header.setProperty("role", "secondary")
        saldos_grid.addWidget(consumidas_header, 0, 1)
        restantes_header = QLabel("Restantes")
        restantes_header.setProperty("role", "secondary")
        saldos_grid.addWidget(restantes_header, 0, 2)

        self.saldo_periodo_label = QLabel("Mensual")
        self.saldo_periodo_consumidas = self._build_saldo_field()
        self.saldo_periodo_restantes = self._build_saldo_field()
        self.saldo_periodo_exceso = self._build_exceso_badge()
        saldos_grid.addWidget(self.saldo_periodo_label, 1, 0)
        saldos_grid.addWidget(self.saldo_periodo_consumidas, 1, 1)
        saldos_grid.addWidget(self.saldo_periodo_restantes, 1, 2)
        saldos_grid.addWidget(self.saldo_periodo_exceso, 1, 3)

        saldos_grid.addWidget(QLabel("Anual delegada"), 2, 0)
        self.saldo_anual_consumidas = self._build_saldo_field()
        self.saldo_anual_restantes = self._build_saldo_field()
        self.saldo_anual_exceso = self._build_exceso_badge()
        saldos_grid.addWidget(self.saldo_anual_consumidas, 2, 1)
        saldos_grid.addWidget(self.saldo_anual_restantes, 2, 2)
        saldos_grid.addWidget(self.saldo_anual_exceso, 2, 3)

        saldos_grid.addWidget(QLabel("Anual grupo"), 3, 0)
        self.saldo_grupo_consumidas = self._build_saldo_field()
        self.saldo_grupo_restantes = self._build_saldo_field()
        self.saldo_grupo_exceso = self._build_exceso_badge()
        saldos_grid.addWidget(self.saldo_grupo_consumidas, 3, 1)
        saldos_grid.addWidget(self.saldo_grupo_restantes, 3, 2)
        saldos_grid.addWidget(self.saldo_grupo_exceso, 3, 3)

        saldos_layout.addLayout(saldos_grid)

        bolsas_title = QLabel("Bolsas")
        bolsas_title.setProperty("role", "secondary")
        saldos_layout.addWidget(bolsas_title)

        bolsas_grid = QGridLayout()
        bolsas_grid.setHorizontalSpacing(10)
        bolsas_grid.setVerticalSpacing(6)
        bolsas_grid.addWidget(QLabel("Bolsa mensual delegada"), 0, 0)
        self.bolsa_mensual_label = QLabel("00:00")
        self.bolsa_mensual_label.setProperty("role", "valueField")
        bolsas_grid.addWidget(self.bolsa_mensual_label, 0, 1)

        bolsas_grid.addWidget(QLabel("Bolsa anual delegada"), 1, 0)
        self.bolsa_delegada_label = QLabel("00:00")
        self.bolsa_delegada_label.setProperty("role", "valueField")
        bolsas_grid.addWidget(self.bolsa_delegada_label, 1, 1)

        bolsas_grid.addWidget(QLabel("Bolsa anual grupo"), 2, 0)
        self.bolsa_grupo_label = QLabel("00:00")
        self.bolsa_grupo_label.setProperty("role", "valueField")
        bolsas_grid.addWidget(self.bolsa_grupo_label, 2, 1)
        saldos_layout.addLayout(bolsas_grid)

        right_column.addWidget(saldos_card)

        historico_card, historico_layout = self._create_card("Histórico", variant="sidebar")
        historico_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._historico_group = historico_card

        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(8)
        filtros_layout.addWidget(QLabel("Periodo"))
        self.periodo_modo_combo = QComboBox()
        self.periodo_modo_combo.addItem("Año completo", "ANUAL")
        self.periodo_modo_combo.addItem("Año + mes", "MENSUAL")
        self.periodo_modo_combo.currentIndexChanged.connect(self._on_period_mode_changed)
        filtros_layout.addWidget(self.periodo_modo_combo)

        filtros_layout.addWidget(QLabel("Año"))
        self.year_input = QSpinBox()
        self.year_input.setRange(2000, 2100)
        self.year_input.setValue(QDate.currentDate().year())
        self.year_input.valueChanged.connect(self._on_period_changed)
        filtros_layout.addWidget(self.year_input)

        self.month_label = QLabel("Mes")
        self.month_combo = QComboBox()
        for month_number, month_name in [
            (1, "Enero"),
            (2, "Febrero"),
            (3, "Marzo"),
            (4, "Abril"),
            (5, "Mayo"),
            (6, "Junio"),
            (7, "Julio"),
            (8, "Agosto"),
            (9, "Septiembre"),
            (10, "Octubre"),
            (11, "Noviembre"),
            (12, "Diciembre"),
        ]:
            self.month_combo.addItem(month_name, month_number)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.currentIndexChanged.connect(self._on_period_changed)
        filtros_layout.addWidget(self.month_label)
        filtros_layout.addWidget(self.month_combo)
        filtros_layout.addStretch(1)
        historico_layout.addLayout(filtros_layout)

        self.historico_table = QTableView()
        self.historico_model = SolicitudesTableModel([])
        self.historico_table.setModel(self.historico_model)
        self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.historico_table.selectionModel().selectionChanged.connect(self._on_historico_selection_changed)
        self.historico_table.setShowGrid(False)
        self.historico_table.setAlternatingRowColors(True)
        self.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.historico_table.setMinimumHeight(280)
        self._configure_solicitudes_table(self.historico_table)
        historico_layout.addWidget(self.historico_table, 1)

        historico_actions = QHBoxLayout()
        historico_actions.setSpacing(8)
        historico_actions.addStretch(1)
        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setProperty("variant", "danger")
        self.eliminar_button.clicked.connect(self._on_eliminar)
        historico_actions.addWidget(self.eliminar_button)

        self.generar_pdf_button = QPushButton("Generar PDF histórico")
        self.generar_pdf_button.setProperty("variant", "secondary")
        self.generar_pdf_button.clicked.connect(self._on_generar_pdf_historico)
        historico_actions.addWidget(self.generar_pdf_button)
        historico_layout.addLayout(historico_actions)

        right_column.addWidget(historico_card, 1)

        self._scroll_area.setWidget(content)
        self.setCentralWidget(self._scroll_area)
        self._update_responsive_columns()
        self._configure_time_placeholders()
        self._on_period_mode_changed()
        self._update_solicitud_preview()
        self._update_action_state()

    def _configure_solicitudes_table(self, table: QTableView) -> None:
        header = table.horizontalHeader()
        header.setMinimumSectionSize(72)
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        table.setColumnWidth(5, 220)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_responsive_columns()

    def _update_responsive_columns(self) -> None:
        if not hasattr(self, "_content_row"):
            return
        available_width = self._scroll_area.viewport().width() if hasattr(self, "_scroll_area") else self.width()
        if available_width < 1200:
            self._content_row.setDirection(QBoxLayout.TopToBottom)
            self._content_row.setStretch(0, 0)
            self._content_row.setStretch(1, 0)
        else:
            self._content_row.setDirection(QBoxLayout.LeftToRight)
            self._content_row.setStretch(0, 3)
            self._content_row.setStretch(1, 2)

    def _build_saldo_field(self) -> QLineEdit:
        field = QLineEdit("00:00")
        field.setReadOnly(True)
        field.setFocusPolicy(Qt.NoFocus)
        field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        field.setProperty("role", "saldo")
        return field

    def _build_exceso_badge(self) -> QLabel:
        badge = QLabel("")
        badge.setProperty("role", "badge")
        badge.setVisible(False)
        return badge

    def _load_personas(self, select_id: int | None = None) -> None:
        self.persona_combo.blockSignals(True)
        self.persona_combo.clear()
        self._personas = list(self._persona_use_cases.listar())
        for persona in self._personas:
            self.persona_combo.addItem(persona.nombre, persona.id)
        self.persona_combo.blockSignals(False)

        if select_id is not None:
            for index in range(self.persona_combo.count()):
                if self.persona_combo.itemData(index) == select_id:
                    self.persona_combo.setCurrentIndex(index)
                    break
        self._on_persona_changed()

    def _current_persona(self) -> PersonaDTO | None:
        index = self.persona_combo.currentIndex()
        if index < 0:
            return None
        persona_id = self.persona_combo.currentData()
        for persona in self._personas:
            if persona.id == persona_id:
                return persona
        return None

    def _on_persona_changed(self) -> None:
        self._clear_pendientes()
        self._update_action_state()
        self._refresh_historico()
        self._refresh_saldos()
        self._update_solicitud_preview()

    def _on_period_changed(self) -> None:
        self._refresh_historico()

    def _on_period_mode_changed(self) -> None:
        modo = self.periodo_modo_combo.currentData()
        is_mensual = modo == "MENSUAL"
        self.month_combo.setEnabled(is_mensual)
        self.month_combo.setVisible(is_mensual)
        self.month_label.setVisible(is_mensual)
        self._on_period_changed()

    def _on_completo_changed(self, checked: bool) -> None:
        self._sync_completo_visibility(checked)
        self._update_solicitud_preview()

    def _on_fecha_changed(self) -> None:
        if self.completo_check.isChecked():
            self.completo_check.setChecked(False)
        self._refresh_saldos()
        self._update_solicitud_preview()

    def _configure_time_placeholders(self) -> None:
        self.desde_placeholder.setVisible(False)
        self.hasta_placeholder.setVisible(False)
        desde_hint = self.desde_container.sizeHint()
        hasta_hint = self.hasta_container.sizeHint()
        self.desde_placeholder.setFixedSize(desde_hint)
        self.hasta_placeholder.setFixedSize(hasta_hint)
        self._sync_completo_visibility(self.completo_check.isChecked())

    def _sync_completo_visibility(self, checked: bool) -> None:
        self.desde_container.setVisible(not checked)
        self.hasta_container.setVisible(not checked)
        self.desde_placeholder.setVisible(checked)
        self.hasta_placeholder.setVisible(checked)

    def _on_edit_grupo(self) -> None:
        dialog = GrupoConfigDialog(self._grupo_use_cases, self)
        if dialog.exec():
            self._refresh_saldos()

    def _on_edit_pdf(self) -> None:
        self._on_edit_grupo()

    def _calculate_preview_minutes(self) -> tuple[int, bool]:
        if self.completo_check.isChecked():
            persona = self._current_persona()
            if persona is None:
                return 0, False
            fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
            try:
                minutos = self._solicitud_use_cases.sugerir_completo_min(persona.id or 0, fecha_pedida)
                return minutos, minutos == 0
            except BusinessRuleError:
                return 0, False
        minutos = self.desde_input.time().secsTo(self.hasta_input.time()) // 60
        return max(0, minutos), False

    def _update_solicitud_preview(self) -> None:
        minutos, warning = self._calculate_preview_minutes()
        etiqueta = "Completo" if self.completo_check.isChecked() else "Total"
        self.total_preview_label.setText(f"{etiqueta}: {self._format_minutes(minutos)}")
        self.cuadrante_warning_label.setVisible(warning)
        self.cuadrante_warning_label.setText("Cuadrante no configurado" if warning else "")

    def _update_action_state(self) -> None:
        persona_selected = self._current_persona() is not None
        self.agregar_button.setEnabled(persona_selected)
        self.confirmar_button.setEnabled(persona_selected and bool(self._pending_solicitudes))
        self.edit_persona_button.setEnabled(persona_selected)
        self.delete_persona_button.setEnabled(persona_selected)
        self.edit_grupo_button.setEnabled(True)
        self.editar_pdf_button.setEnabled(True)
        self.eliminar_button.setEnabled(persona_selected and self._selected_historico() is not None)
        self.eliminar_pendiente_button.setEnabled(persona_selected and bool(self._pending_solicitudes))
        self.generar_pdf_button.setEnabled(persona_selected and self.historico_model.rowCount() > 0)

    def _selected_historico(self) -> SolicitudDTO | None:
        selection = self.historico_table.selectionModel().selectedRows()
        if not selection:
            return None
        return self.historico_model.solicitud_at(selection[0].row())

    def _on_add_persona(self) -> None:
        dialog = PersonaDialog(self)
        persona_dto = dialog.get_persona()
        if persona_dto is None:
            logger.info("Creación de persona cancelada")
            return
        try:
            creada = self._persona_use_cases.crear(persona_dto)
        except ValidacionError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error creando persona")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._load_personas(select_id=creada.id)

    def _on_edit_persona(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        dialog = PersonaDialog(self, persona)
        persona_dto = dialog.get_persona()
        if persona_dto is None:
            logger.info("Edición de persona cancelada")
            return
        confirm = QMessageBox.question(
            self,
            "Confirmar cambios",
            "¿Confirmas los cambios? Esto afectará a cálculos futuros.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            actualizada = self._persona_use_cases.editar_persona(persona_dto)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error editando persona")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._load_personas(select_id=actualizada.id)

    def _on_delete_persona(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        respuesta = QMessageBox.question(
            self,
            "Eliminar delegado",
            f"¿Deseas deshabilitar a {persona.nombre}? El histórico se conservará.",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        try:
            self._persona_use_cases.desactivar_persona(persona.id or 0)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error deshabilitando delegado")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._load_personas()

    def _on_add_pendiente(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
        completo = self.completo_check.isChecked()
        desde = None if completo else self.desde_input.time().toString("HH:mm")
        hasta = None if completo else self.hasta_input.time().toString("HH:mm")
        minutos, _warning = self._calculate_preview_minutes()
        notas_text = self.notas_input.toPlainText().strip()
        notas = notas_text or None
        solicitud = SolicitudDTO(
            id=None,
            persona_id=persona.id or 0,
            fecha_solicitud=datetime.now().strftime("%Y-%m-%d"),
            fecha_pedida=fecha_pedida,
            desde=desde,
            hasta=hasta,
            completo=completo,
            horas=minutos / 60 if minutos > 0 else 0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
            notas=notas,
        )
        if not self._resolve_pending_conflict(fecha_pedida, completo):
            return
        if not self._resolve_backend_conflict(persona.id or 0, solicitud):
            return
        self._pending_solicitudes.append(solicitud)
        self.pendientes_model.append_solicitud(solicitud)
        self.notas_input.setPlainText("")
        self._refresh_saldos()
        self._update_action_state()

    def _resolve_pending_conflict(self, fecha_pedida: str, completo: bool) -> bool:
        conflictos = [
            index
            for index, solicitud in enumerate(self._pending_solicitudes)
            if solicitud.fecha_pedida == fecha_pedida and solicitud.completo != completo
        ]
        if not conflictos:
            return True
        mensaje = (
            "Hay horas parciales. ¿Sustituirlas por COMPLETO?"
            if completo
            else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
        )
        if not self._confirm_conflicto(mensaje):
            return False
        for index in reversed(conflictos):
            self._pending_solicitudes.pop(index)
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        return True

    def _resolve_backend_conflict(self, persona_id: int, solicitud: SolicitudDTO) -> bool:
        try:
            return self._solicitud_use_cases.validar_conflicto_persona(persona_id, solicitud)
        except BusinessRuleError as exc:
            return self._confirm_conflicto(str(exc))

    def _on_confirmar(self) -> None:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return
        try:
            creadas = self._solicitud_use_cases.confirmar_pendientes(persona.id or 0, self._pending_solicitudes)
            pdf_path = self._solicitud_use_cases.generar_pdf_solicitudes(persona.id or 0, creadas)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error confirmando solicitudes")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._clear_pendientes()
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self._show_pdf_result(pdf_path)

    def _show_pdf_result(self, pdf_path: str) -> None:
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("PDF generado")
        mensaje.setText(f"PDF generado en:\n{pdf_path}")
        open_button = mensaje.addButton("Abrir", QMessageBox.ActionRole)
        copy_button = mensaje.addButton("Copiar ruta", QMessageBox.ActionRole)
        mensaje.addButton(QMessageBox.Ok)
        if not self.abrir_pdf_check.isChecked():
            open_button.setVisible(False)
        mensaje.exec()
        clicked = mensaje.clickedButton()
        if clicked == open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif clicked == copy_button:
            QApplication.clipboard().setText(pdf_path)

    def _on_generar_pdf_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        filtro = self._current_periodo_filtro()
        default_name = (
            f"historico_{persona.nombre}_{filtro.year}_{filtro.month or 'anual'}.pdf".replace(" ", "_")
        )
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF histórico",
            str(Path.home() / default_name),
            "PDF (*.pdf)",
        )
        if not output_path:
            return
        try:
            saved_path = self._solicitud_use_cases.generar_pdf_historico(
                persona.id or 0,
                filtro,
                output_path,
            )
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error generando PDF histórico")
            QMessageBox.critical(self, "Error", str(exc))
            return

        if self.abrir_pdf_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(saved_path))

    def _on_eliminar(self) -> None:
        solicitud = self._selected_historico()
        if solicitud is None or solicitud.id is None:
            return
        try:
            self._solicitud_use_cases.eliminar_solicitud(solicitud.id)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error eliminando solicitud")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()

    def _on_remove_pendiente(self) -> None:
        selection = self.pendientes_table.selectionModel().selectedRows()
        if not selection:
            return
        rows = sorted((index.row() for index in selection), reverse=True)
        for row in rows:
            if 0 <= row < len(self._pending_solicitudes):
                self._pending_solicitudes.pop(row)
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._refresh_saldos()
        self._update_action_state()

    def _refresh_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            self.historico_model.set_solicitudes([])
            return
        filtro = self._current_periodo_filtro()
        solicitudes = list(
            self._solicitud_use_cases.listar_solicitudes_por_persona_y_periodo(
                persona.id or 0,
                filtro.year,
                filtro.month,
            )
        )
        self.historico_model.set_solicitudes(solicitudes)
        self._update_action_state()

    def _refresh_saldos(self) -> None:
        filtro = self._current_saldo_filtro()
        self._update_periodo_label(filtro)
        persona = self._current_persona()
        if persona is None:
            self._set_saldos_labels(None)
            return
        try:
            resumen = self._solicitud_use_cases.calcular_resumen_saldos(persona.id or 0, filtro)
            pendientes_periodo = self._pending_minutes_for_period(filtro)
            pendientes_ano = self._pending_minutes_for_period(PeriodoFiltro.anual(filtro.year))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(resumen, pendientes_periodo, pendientes_ano)

    def _update_periodo_label(self, filtro: PeriodoFiltro) -> None:
        if filtro.month is None:
            self.saldo_periodo_label.setText("Mensual")
            return
        self.saldo_periodo_label.setText(f"Mensual ({filtro.month:02d}/{filtro.year})")

    def _set_saldos_labels(
        self,
        resumen,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
    ) -> None:
        if resumen is None:
            self._set_saldo_line(self.saldo_periodo_consumidas, self.saldo_periodo_restantes, self.saldo_periodo_exceso, 0, 0)
            self._set_saldo_line(self.saldo_anual_consumidas, self.saldo_anual_restantes, self.saldo_anual_exceso, 0, 0)
            self._set_saldo_line(self.saldo_grupo_consumidas, self.saldo_grupo_restantes, self.saldo_grupo_exceso, 0, 0)
            self._set_bolsa_labels(0, 0, 0)
            return
        consumidas_periodo = resumen.individual.consumidas_periodo_min + pendientes_periodo
        bolsa_periodo = resumen.individual.bolsa_periodo_min
        restantes_periodo = bolsa_periodo - consumidas_periodo

        consumidas_anual = resumen.individual.consumidas_anual_min + pendientes_ano
        bolsa_anual = resumen.individual.bolsa_anual_min
        restantes_anual = bolsa_anual - consumidas_anual

        consumidas_grupo = resumen.grupo_anual.consumidas_anual_min + pendientes_ano
        bolsa_grupo = resumen.grupo_anual.bolsa_anual_grupo_min
        restantes_grupo = bolsa_grupo - consumidas_grupo

        self._set_saldo_line(
            self.saldo_periodo_consumidas,
            self.saldo_periodo_restantes,
            self.saldo_periodo_exceso,
            consumidas_periodo,
            restantes_periodo,
        )
        self._set_saldo_line(
            self.saldo_anual_consumidas,
            self.saldo_anual_restantes,
            self.saldo_anual_exceso,
            consumidas_anual,
            restantes_anual,
        )
        self._set_saldo_line(
            self.saldo_grupo_consumidas,
            self.saldo_grupo_restantes,
            self.saldo_grupo_exceso,
            consumidas_grupo,
            restantes_grupo,
        )
        self._set_bolsa_labels(bolsa_periodo, bolsa_anual, bolsa_grupo)

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _current_periodo_filtro(self) -> PeriodoFiltro:
        year = self.year_input.value()
        modo = self.periodo_modo_combo.currentData()
        if modo == "ANUAL":
            return PeriodoFiltro.anual(year)
        return PeriodoFiltro.mensual(year, self.month_combo.currentData())

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        fecha = self.fecha_input.date()
        return PeriodoFiltro.mensual(fecha.year(), fecha.month())

    def _pending_minutes_for_period(self, filtro: PeriodoFiltro) -> int:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return 0
        pendientes_filtrados = []
        for solicitud in self._pending_solicitudes:
            fecha = datetime.strptime(solicitud.fecha_pedida, "%Y-%m-%d")
            if fecha.year != filtro.year:
                continue
            if filtro.modo == "MENSUAL" and fecha.month != filtro.month:
                continue
            pendientes_filtrados.append(solicitud)
        if not pendientes_filtrados:
            return 0
        try:
            return self._solicitud_use_cases.sumar_pendientes_min(persona.id or 0, pendientes_filtrados)
        except BusinessRuleError:
            return 0

    def _clear_pendientes(self) -> None:
        self._pending_solicitudes = []
        self.pendientes_model.clear()
        self._update_action_state()

    def _set_saldo_line(
        self,
        consumidas_field: QLineEdit,
        restantes_field: QLineEdit,
        badge: QLabel,
        consumidas: int,
        restantes: int,
    ) -> None:
        consumidas_field.setText(self._format_minutes(consumidas))
        restantes_text, warning, exceso = self._format_restantes(restantes)
        restantes_field.setText(restantes_text)
        self._set_warning_state(restantes_field, warning)
        badge.setText(exceso)
        badge.setVisible(bool(exceso))

    def _set_warning_state(self, field: QLineEdit, warning: bool) -> None:
        field.setProperty("status", "warning" if warning else None)
        field.style().unpolish(field)
        field.style().polish(field)
        field.update()

    def _set_bolsa_labels(self, bolsa_mensual: int, bolsa_delegada: int, bolsa_grupo: int) -> None:
        self.bolsa_mensual_label.setText(self._format_minutes(bolsa_mensual))
        self.bolsa_delegada_label.setText(self._format_minutes(bolsa_delegada))
        self.bolsa_grupo_label.setText(self._format_minutes(bolsa_grupo))

    def _format_restantes(self, minutos: int) -> tuple[str, bool, str]:
        if minutos < 0:
            return "00:00", True, f"Exceso {minutes_to_hhmm(abs(minutos))}"
        return self._format_minutes(minutos), False, ""

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
