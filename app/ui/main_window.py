from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QApplication,
    QSpinBox,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.dto import PersonaDTO, SolicitudDTO
from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
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
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = HeaderWidget()
        layout.addWidget(header)

        persona_row = QHBoxLayout()
        persona_row.addWidget(QLabel("Persona"))
        self.persona_combo = QComboBox()
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        persona_row.addWidget(self.persona_combo)

        self.edit_persona_button = QPushButton("Editar persona")
        self.edit_persona_button.setProperty("variant", "secondary")
        self.edit_persona_button.clicked.connect(self._on_edit_persona)
        persona_row.addWidget(self.edit_persona_button)

        self.add_persona_button = QPushButton("Nueva persona")
        self.add_persona_button.setProperty("variant", "secondary")
        self.add_persona_button.clicked.connect(self._on_add_persona)
        persona_row.addWidget(self.add_persona_button)
        persona_row.addStretch(1)
        layout.addLayout(persona_row)

        solicitud_group = QGroupBox("Nueva solicitud")
        solicitud_layout = QFormLayout(solicitud_group)
        self.fecha_input = QDateEdit(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        solicitud_layout.addRow("Fecha", self.fecha_input)

        self.desde_input = QTimeEdit(QTime(9, 0))
        self.desde_input.setDisplayFormat("HH:mm")
        solicitud_layout.addRow("Desde", self.desde_input)

        self.hasta_input = QTimeEdit(QTime(17, 0))
        self.hasta_input.setDisplayFormat("HH:mm")
        solicitud_layout.addRow("Hasta", self.hasta_input)

        self.completo_check = QCheckBox("Completo")
        self.completo_check.toggled.connect(self._on_completo_changed)
        solicitud_layout.addRow(self.completo_check)

        self.horas_input = QDoubleSpinBox()
        self.horas_input.setRange(0, 24)
        self.horas_input.setDecimals(2)
        solicitud_layout.addRow("Horas", self.horas_input)

        self.agregar_button = QPushButton("Agregar")
        self.agregar_button.setProperty("variant", "primary")
        self.agregar_button.clicked.connect(self._on_add_pendiente)
        solicitud_layout.addRow(self.agregar_button)
        layout.addWidget(solicitud_group)

        pendientes_group = QGroupBox("Pendientes de confirmar")
        pendientes_layout = QVBoxLayout(pendientes_group)
        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setAlternatingRowColors(True)
        pendientes_layout.addWidget(self.pendientes_table)
        layout.addWidget(pendientes_group)

        self.confirmar_button = QPushButton("Confirmar / Generar PDF")
        self.confirmar_button.setProperty("variant", "primary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        layout.addWidget(self.confirmar_button)

        periodo_group = QGroupBox("Periodo")
        periodo_layout = QHBoxLayout(periodo_group)
        self.year_input = QSpinBox()
        self.year_input.setRange(2000, 2100)
        self.year_input.setValue(QDate.currentDate().year())
        self.year_input.valueChanged.connect(self._on_period_changed)
        periodo_layout.addWidget(QLabel("Año"))
        periodo_layout.addWidget(self.year_input)

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
        periodo_layout.addWidget(QLabel("Mes"))
        periodo_layout.addWidget(self.month_combo)
        periodo_layout.addStretch(1)
        layout.addWidget(periodo_group)

        historico_group = QGroupBox("Histórico")
        historico_layout = QVBoxLayout(historico_group)
        self.historico_table = QTableView()
        self.historico_model = SolicitudesTableModel([])
        self.historico_table.setModel(self.historico_model)
        self.historico_table.setSelectionBehavior(QTableView.SelectRows)
        self.historico_table.setSelectionMode(QTableView.SingleSelection)
        self.historico_table.selectionModel().selectionChanged.connect(
            self._on_historico_selection_changed
        )
        self.historico_table.setAlternatingRowColors(True)
        historico_layout.addWidget(self.historico_table)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setProperty("variant", "danger")
        self.eliminar_button.clicked.connect(self._on_eliminar)
        historico_layout.addWidget(self.eliminar_button)
        layout.addWidget(historico_group)

        saldos_group = QGroupBox("Saldos")
        saldos_layout = QFormLayout(saldos_group)
        self.consumidas_mes_label = QLabel("0.00")
        self.restantes_mes_label = QLabel("0.00")
        self.exceso_mes_label = QLabel("0.00")
        self.consumidas_ano_label = QLabel("0.00")
        self.restantes_ano_label = QLabel("0.00")
        self.exceso_ano_label = QLabel("0.00")

        saldos_layout.addRow("Consumidas mes", self.consumidas_mes_label)
        saldos_layout.addRow("Restantes mes", self.restantes_mes_label)
        saldos_layout.addRow("Exceso mes", self.exceso_mes_label)
        saldos_layout.addRow("Consumidas año", self.consumidas_ano_label)
        saldos_layout.addRow("Restantes año", self.restantes_ano_label)
        saldos_layout.addRow("Exceso año", self.exceso_ano_label)
        layout.addWidget(saldos_group)

        self.setCentralWidget(central)
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
        self._pending_solicitudes = []
        self.pendientes_model.clear()
        self._update_action_state()
        self._refresh_historico()
        self._refresh_saldos()
        if self.completo_check.isChecked():
            self._set_horas_defecto()

    def _on_period_changed(self) -> None:
        self._refresh_historico()
        self._refresh_saldos()

    def _on_completo_changed(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        if checked:
            self._set_horas_defecto()
        else:
            self.horas_input.setValue(0.0)

    def _set_horas_defecto(self) -> None:
        persona = self._current_persona()
        if persona is None:
            self.horas_input.setValue(0.0)
        else:
            self.horas_input.setValue(persona.horas_jornada_defecto)

    def _update_action_state(self) -> None:
        persona_selected = self._current_persona() is not None
        self.agregar_button.setEnabled(persona_selected)
        self.confirmar_button.setEnabled(persona_selected and bool(self._pending_solicitudes))
        self.edit_persona_button.setEnabled(persona_selected)
        self.eliminar_button.setEnabled(persona_selected and self._selected_historico() is not None)

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
        solicitud = SolicitudDTO(
            id=None,
            persona_id=persona.id or 0,
            fecha_solicitud=datetime.now().strftime("%Y-%m-%d"),
            fecha_pedida=fecha_pedida,
            desde=desde,
            hasta=hasta,
            completo=completo,
            horas=self.horas_input.value(),
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
        )
        self._pending_solicitudes.append(solicitud)
        self.pendientes_model.append_solicitud(solicitud)
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

    def _refresh_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            self.historico_model.set_solicitudes([])
            return
        year = self.year_input.value()
        month = self.month_combo.currentData()
        solicitudes = list(
            self._solicitud_use_cases.listar_solicitudes_por_persona_y_periodo(
                persona.id or 0,
                year,
                month,
            )
        )
        self.historico_model.set_solicitudes(solicitudes)
        self._update_action_state()

    def _refresh_saldos(self) -> None:
        persona = self._current_persona()
        if persona is None:
            self._set_saldos_labels(None)
            return
        year = self.year_input.value()
        month = self.month_combo.currentData()
        try:
            saldos = self._solicitud_use_cases.calcular_saldos(persona.id or 0, year, month)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(saldos)

    def _set_saldos_labels(self, saldos) -> None:
        if saldos is None:
            self.consumidas_mes_label.setText("0.00")
            self.restantes_mes_label.setText("0.00")
            self.exceso_mes_label.setText("0.00")
            self.consumidas_ano_label.setText("0.00")
            self.restantes_ano_label.setText("0.00")
            self.exceso_ano_label.setText("0.00")
            self.exceso_mes_label.setStyleSheet("")
            self.exceso_ano_label.setStyleSheet("")
            return
        self.consumidas_mes_label.setText(f"{saldos.consumidas_mes:.2f}")
        self.restantes_mes_label.setText(f"{saldos.restantes_mes:.2f}")
        self.exceso_mes_label.setText(f"{saldos.exceso_mes:.2f}")
        self.consumidas_ano_label.setText(f"{saldos.consumidas_ano:.2f}")
        self.restantes_ano_label.setText(f"{saldos.restantes_ano:.2f}")
        self.exceso_ano_label.setText(f"{saldos.exceso_ano:.2f}")
        self.exceso_mes_label.setStyleSheet("color: red;" if saldos.exceso_mes > 0 else "")
        self.exceso_ano_label.setStyleSheet("color: red;" if saldos.exceso_ano > 0 else "")

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()
