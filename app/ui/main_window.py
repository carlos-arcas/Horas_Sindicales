from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QApplication,
    QAbstractItemView,
    QScrollArea,
    QSpinBox,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_utils import minutes_to_hhmm
from app.pdf import service as pdf
from app.ui.models_qt import SolicitudesTableModel
from app.ui.person_dialog import PersonaDialog
from app.ui.style import apply_theme
from app.ui.widgets.header import HeaderWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, persona_use_cases: PersonaUseCases, solicitud_use_cases: SolicitudUseCases) -> None:
        super().__init__()
        app = QApplication.instance()
        if app:
            apply_theme(app)
        self._persona_use_cases = persona_use_cases
        self._solicitud_use_cases = solicitud_use_cases
        self._personas: list[PersonaDTO] = []
        self._pending_solicitudes: list[SolicitudDTO] = []
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self._load_personas()

    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = HeaderWidget()
        layout.addWidget(header)

        persona_row = QHBoxLayout()
        persona_row.addWidget(QLabel("Delegado"))
        self.persona_combo = QComboBox()
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        persona_row.addWidget(self.persona_combo)

        self.edit_persona_button = QPushButton("Editar delegado")
        self.edit_persona_button.setProperty("variant", "secondary")
        self.edit_persona_button.clicked.connect(self._on_edit_persona)
        persona_row.addWidget(self.edit_persona_button)

        self.add_persona_button = QPushButton("Nuevo delegado")
        self.add_persona_button.setProperty("variant", "secondary")
        self.add_persona_button.clicked.connect(self._on_add_persona)
        persona_row.addWidget(self.add_persona_button)
        persona_row.addStretch(1)
        layout.addLayout(persona_row)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)
        layout.addLayout(main_layout)

        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        main_layout.addLayout(left_column, 3)

        solicitud_group = QGroupBox("Alta de solicitud")
        solicitud_layout = QHBoxLayout(solicitud_group)
        solicitud_layout.setSpacing(10)

        self.fecha_input = QDateEdit(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.dateChanged.connect(self._update_solicitud_preview)
        solicitud_layout.addWidget(QLabel("Fecha"))
        solicitud_layout.addWidget(self.fecha_input)

        self.desde_input = QTimeEdit(QTime(9, 0))
        self.desde_input.setDisplayFormat("HH:mm")
        self.desde_input.timeChanged.connect(self._update_solicitud_preview)
        solicitud_layout.addWidget(QLabel("Desde"))
        solicitud_layout.addWidget(self.desde_input)

        self.hasta_input = QTimeEdit(QTime(17, 0))
        self.hasta_input.setDisplayFormat("HH:mm")
        self.hasta_input.timeChanged.connect(self._update_solicitud_preview)
        solicitud_layout.addWidget(QLabel("Hasta"))
        solicitud_layout.addWidget(self.hasta_input)

        self.completo_check = QCheckBox("Completo")
        self.completo_check.toggled.connect(self._on_completo_changed)
        solicitud_layout.addWidget(self.completo_check)

        self.total_preview_label = QLabel("Total: 00:00")
        self.total_preview_label.setProperty("role", "secondary")
        solicitud_layout.addWidget(self.total_preview_label)

        self.agregar_button = QPushButton("Agregar")
        self.agregar_button.setProperty("variant", "primary")
        self.agregar_button.clicked.connect(self._on_add_pendiente)
        solicitud_layout.addWidget(self.agregar_button)
        solicitud_layout.addStretch(1)
        left_column.addWidget(solicitud_group)

        pendientes_group = QGroupBox("Pendientes de confirmar")
        pendientes_layout = QVBoxLayout(pendientes_group)
        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pendientes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pendientes_table.setAlternatingRowColors(True)

        self.pendientes_table.setMinimumHeight(220)
        pendientes_layout.addWidget(self.pendientes_table)

        pendientes_actions = QHBoxLayout()
        self.eliminar_pendiente_button = QPushButton("Eliminar seleccionado")
        self.eliminar_pendiente_button.setProperty("variant", "danger")
        self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
        pendientes_actions.addWidget(self.eliminar_pendiente_button)
        pendientes_actions.addStretch(1)

        self.confirmar_button = QPushButton("Confirmar y Generar PDF")
        self.confirmar_button.setProperty("variant", "primary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        pendientes_actions.addWidget(self.confirmar_button)
        pendientes_layout.addLayout(pendientes_actions)
        left_column.addWidget(pendientes_group)

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        main_layout.addLayout(right_column, 2)

        saldos_group = QGroupBox("Resumen de saldos")
        saldos_layout = QFormLayout(saldos_group)
        self.saldo_periodo_label = QLabel("00:00")
        self.saldo_anual_label = QLabel("00:00")
        self.total_global_label = QLabel("00:00")
        saldos_layout.addRow("Saldo delegado (periodo)", self.saldo_periodo_label)
        saldos_layout.addRow("Saldo anual delegado", self.saldo_anual_label)
        saldos_layout.addRow("Total global periodo", self.total_global_label)
        right_column.addWidget(saldos_group)

        historico_group = QGroupBox("Histórico")
        historico_layout = QVBoxLayout(historico_group)

        filtros_layout = QHBoxLayout()
        self.periodo_modo_combo = QComboBox()
        self.periodo_modo_combo.addItem("Año completo", "ANUAL")
        self.periodo_modo_combo.addItem("Año + mes", "MENSUAL")
        self.periodo_modo_combo.currentIndexChanged.connect(self._on_period_mode_changed)
        filtros_layout.addWidget(QLabel("Periodo"))
        filtros_layout.addWidget(self.periodo_modo_combo)

        self.year_input = QSpinBox()
        self.year_input.setRange(2000, 2100)
        self.year_input.setValue(QDate.currentDate().year())
        self.year_input.valueChanged.connect(self._on_period_changed)
        filtros_layout.addWidget(QLabel("Año"))
        filtros_layout.addWidget(self.year_input)

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
        filtros_layout.addWidget(QLabel("Mes"))
        filtros_layout.addWidget(self.month_combo)
        filtros_layout.addStretch(1)
        historico_layout.addLayout(filtros_layout)

        self.historico_table = QTableView()
        self.historico_model = SolicitudesTableModel([])
        self.historico_table.setModel(self.historico_model)
        self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.historico_table.selectionModel().selectionChanged.connect(
            self._on_historico_selection_changed
        )
        self.historico_table.setAlternatingRowColors(True)

        self.historico_table.setMinimumHeight(260)
        historico_layout.addWidget(self.historico_table)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setProperty("variant", "danger")
        self.eliminar_button.clicked.connect(self._on_eliminar)
        historico_layout.addWidget(self.eliminar_button)
        right_column.addWidget(historico_group)
        right_column.addStretch(1)

        self.setCentralWidget(scroll_area)
        self._on_period_mode_changed()
        self._update_action_state()

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
        self._clear_pendientes()
        self._refresh_historico()
        self._refresh_saldos()

    def _on_period_mode_changed(self) -> None:
        modo = self.periodo_modo_combo.currentData()
        is_mensual = modo == "MENSUAL"
        self.month_combo.setEnabled(is_mensual)
        self._on_period_changed()

    def _on_completo_changed(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        self._update_solicitud_preview()

    def _calculate_preview_minutes(self) -> int:
        if self.completo_check.isChecked():
            persona = self._current_persona()
            if persona is None:
                return 0
            fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
            try:
                return self._solicitud_use_cases.sugerir_completo_min(persona.id or 0, fecha_pedida)
            except BusinessRuleError:
                return 0
        minutos = self.desde_input.time().secsTo(self.hasta_input.time()) // 60
        return max(0, minutos)

    def _update_solicitud_preview(self) -> None:
        minutos = self._calculate_preview_minutes()
        etiqueta = "Completo" if self.completo_check.isChecked() else "Total"
        self.total_preview_label.setText(f"{etiqueta}: {self._format_minutes(minutos)}")

    def _update_action_state(self) -> None:
        persona_selected = self._current_persona() is not None
        self.agregar_button.setEnabled(persona_selected)
        self.confirmar_button.setEnabled(persona_selected and bool(self._pending_solicitudes))
        self.edit_persona_button.setEnabled(persona_selected)
        self.eliminar_button.setEnabled(persona_selected and self._selected_historico() is not None)
        self.eliminar_pendiente_button.setEnabled(persona_selected and bool(self._pending_solicitudes))

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

    def _on_add_pendiente(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
        completo = self.completo_check.isChecked()
        desde = None if completo else self.desde_input.time().toString("HH:mm")
        hasta = None if completo else self.hasta_input.time().toString("HH:mm")
        minutos = self._calculate_preview_minutes()
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
        )
        self._pending_solicitudes.append(solicitud)
        self.pendientes_model.append_solicitud(solicitud)
        self._refresh_saldos()
        self._update_action_state()

    def _on_confirmar(self) -> None:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return
        creadas: list[SolicitudDTO] = []
        pendientes_restantes: list[SolicitudDTO] = []
        errores: list[str] = []
        for solicitud in self._pending_solicitudes:
            try:
                creada, _ = self._solicitud_use_cases.agregar_solicitud(solicitud)
                creadas.append(creada)
            except (ValidacionError, BusinessRuleError) as exc:
                errores.append(str(exc))
                pendientes_restantes.append(solicitud)
            except Exception as exc:  # pragma: no cover - fallback
                logger.exception("Error creando solicitud")
                errores.append(str(exc))
                pendientes_restantes.append(solicitud)
        if creadas:
            pdf.generate(creadas)
        if errores:
            QMessageBox.warning(self, "Errores", "\n".join(errores))
        self._pending_solicitudes = pendientes_restantes
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()

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
        persona = self._current_persona()
        if persona is None:
            self._set_saldos_labels(None)
            return
        try:
            filtro = self._current_periodo_filtro()
            saldos = self._solicitud_use_cases.calcular_saldos_por_periodo(
                persona.id or 0, filtro
            )
            pendientes_periodo = self._pending_minutes_for_period(filtro)
            pendientes_ano = self._pending_minutes_for_period(PeriodoFiltro.anual(filtro.year))
            totales = self._solicitud_use_cases.calcular_totales_globales(filtro)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(saldos, pendientes_periodo, pendientes_ano, totales.total_restantes_min)

    def _set_saldos_labels(
        self,
        saldos,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
        total_global: int = 0,
    ) -> None:
        if saldos is None:
            self.saldo_periodo_label.setText("00:00")
            self.saldo_anual_label.setText("00:00")
            self.total_global_label.setText("00:00")
            self.saldo_periodo_label.setStyleSheet("")
            self.saldo_anual_label.setStyleSheet("")
            self.total_global_label.setStyleSheet("")
            return
        restantes_periodo = saldos.restantes_mes - pendientes_periodo
        restantes_ano = saldos.restantes_ano - pendientes_ano
        total_global_restante = total_global - pendientes_periodo

        self.saldo_periodo_label.setText(self._format_minutes(restantes_periodo))
        self.saldo_anual_label.setText(self._format_minutes(restantes_ano))
        self.total_global_label.setText(self._format_minutes(total_global_restante))
        self.saldo_periodo_label.setStyleSheet("color: #d0001a;" if restantes_periodo < 0 else "")
        self.saldo_anual_label.setStyleSheet("color: #d0001a;" if restantes_ano < 0 else "")
        self.total_global_label.setStyleSheet("color: #d0001a;" if total_global_restante < 0 else "")

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _current_periodo_filtro(self) -> PeriodoFiltro:
        year = self.year_input.value()
        modo = self.periodo_modo_combo.currentData()
        if modo == "ANUAL":
            return PeriodoFiltro.anual(year)
        return PeriodoFiltro.mensual(year, self.month_combo.currentData())

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
            return self._solicitud_use_cases.sumar_pendientes_min(
                persona.id or 0, pendientes_filtrados
            )
        except BusinessRuleError:
            return 0

    def _clear_pendientes(self) -> None:
        self._pending_solicitudes = []
        self.pendientes_model.clear()
        self._update_action_state()

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
