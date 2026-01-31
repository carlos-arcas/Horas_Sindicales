from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, QTime, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
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
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_utils import minutes_to_hhmm
from app.ui.models_qt import SolicitudesTableModel
from app.ui.group_dialog import GrupoConfigDialog
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

    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        layout.addLayout(top_row)

        left_top = QVBoxLayout()
        left_top.setSpacing(10)
        top_row.addLayout(left_top, 3)

        right_top = QVBoxLayout()
        right_top.setSpacing(10)
        top_row.addLayout(right_top, 2)

        header = HeaderWidget()
        left_top.addWidget(header)

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

        self.edit_grupo_button = QPushButton("Editar grupo")
        self.edit_grupo_button.setProperty("variant", "secondary")
        self.edit_grupo_button.clicked.connect(self._on_edit_grupo)
        persona_row.addWidget(self.edit_grupo_button)

        persona_row.addStretch(1)
        left_top.addLayout(persona_row)

        saldos_group = QGroupBox("Resumen de saldos")
        saldos_layout = QFormLayout(saldos_group)
        self.saldo_periodo_label = QLabel("00:00")
        self.saldo_anual_label = QLabel("00:00")
        self.saldo_global_label = QLabel("00:00")
        self.saldo_grupo_label = QLabel("00:00")
        saldos_layout.addRow("Periodo", self.saldo_periodo_label)
        saldos_layout.addRow("Anual delegado", self.saldo_anual_label)
        saldos_layout.addRow("Anual global", self.saldo_global_label)
        saldos_layout.addRow("Anual grupo", self.saldo_grupo_label)
        right_top.addWidget(saldos_group)
        right_top.addStretch(1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        layout.addLayout(bottom_row, 1)

        left_bottom = QVBoxLayout()
        left_bottom.setSpacing(12)
        bottom_row.addLayout(left_bottom, 3)

        solicitud_group = QGroupBox("Alta de solicitud")
        solicitud_layout = QVBoxLayout(solicitud_group)
        solicitud_layout.setSpacing(8)

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

        self.agregar_button = QPushButton("Agregar")
        self.agregar_button.setProperty("variant", "primary")
        self.agregar_button.clicked.connect(self._on_add_pendiente)
        solicitud_row.addWidget(self.agregar_button)
        solicitud_row.addStretch(1)
        solicitud_layout.addLayout(solicitud_row)

        notas_row = QHBoxLayout()
        notas_row.addWidget(QLabel("Notas"))
        self.notas_input = QPlainTextEdit()
        self.notas_input.setPlaceholderText("Notas para la solicitud")
        self.notas_input.setFixedHeight(70)
        notas_row.addWidget(self.notas_input, 1)
        solicitud_layout.addLayout(notas_row)

        left_bottom.addWidget(solicitud_group)

        pendientes_group = QGroupBox("Pendientes de confirmar")
        pendientes_layout = QVBoxLayout(pendientes_group)
        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pendientes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pendientes_table.setAlternatingRowColors(True)
        self.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pendientes_table.setMinimumHeight(220)
        pendientes_layout.addWidget(self.pendientes_table, 1)

        pendientes_actions = QHBoxLayout()
        self.eliminar_pendiente_button = QPushButton("Eliminar seleccionado")
        self.eliminar_pendiente_button.setProperty("variant", "danger")
        self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
        pendientes_actions.addWidget(self.eliminar_pendiente_button)
        self.abrir_pdf_check = QCheckBox("Abrir PDF al finalizar")
        self.abrir_pdf_check.setChecked(True)
        pendientes_actions.addWidget(self.abrir_pdf_check)
        pendientes_actions.addStretch(1)

        self.confirmar_button = QPushButton("Confirmar y Generar PDF")
        self.confirmar_button.setProperty("variant", "primary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        pendientes_actions.addWidget(self.confirmar_button)
        pendientes_layout.addLayout(pendientes_actions)
        left_bottom.addWidget(pendientes_group, 1)

        right_bottom = QVBoxLayout()
        right_bottom.setSpacing(12)
        bottom_row.addLayout(right_bottom, 2)

        historico_group = QGroupBox("Histórico")
        historico_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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

        historico_actions = QHBoxLayout()
        self.generar_pdf_button = QPushButton("Generar PDF histórico")
        self.generar_pdf_button.setProperty("variant", "secondary")
        self.generar_pdf_button.clicked.connect(self._on_generar_pdf_historico)
        historico_actions.addWidget(self.generar_pdf_button)
        historico_actions.addStretch(1)
        historico_layout.addLayout(historico_actions)

        self.historico_table = QTableView()
        self.historico_model = SolicitudesTableModel([])
        self.historico_table.setModel(self.historico_model)
        self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.historico_table.selectionModel().selectionChanged.connect(
            self._on_historico_selection_changed
        )
        self.historico_table.setAlternatingRowColors(True)
        self.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.historico_table.setMinimumHeight(260)
        historico_layout.addWidget(self.historico_table, 1)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setProperty("variant", "danger")
        self.eliminar_button.clicked.connect(self._on_eliminar)
        historico_layout.addWidget(self.eliminar_button)
        right_bottom.addWidget(historico_group, 1)

        self.setCentralWidget(scroll_area)
        self._configure_time_placeholders()
        self._on_period_mode_changed()
        self._update_solicitud_preview()
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
        self.month_combo.setVisible(is_mensual)
        self.month_label.setVisible(is_mensual)
        self._on_period_changed()

    def _on_completo_changed(self, checked: bool) -> None:
        self._sync_completo_visibility(checked)
        self._update_solicitud_preview()

    def _on_fecha_changed(self) -> None:
        if self.completo_check.isChecked():
            self.completo_check.setChecked(False)
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
        self.edit_grupo_button.setEnabled(True)
        self.eliminar_button.setEnabled(persona_selected and self._selected_historico() is not None)
        self.eliminar_pendiente_button.setEnabled(persona_selected and bool(self._pending_solicitudes))
        self.generar_pdf_button.setEnabled(
            persona_selected and self.historico_model.rowCount() > 0
        )

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
        for index in sorted(conflictos, reverse=True):
            self._pending_solicitudes.pop(index)
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        return True

    def _resolve_backend_conflict(self, persona_id: int, solicitud: SolicitudDTO) -> bool:
        try:
            conflicto = self._solicitud_use_cases.validar_conflicto_dia(
                persona_id, solicitud.fecha_pedida, solicitud.completo
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return False
        if conflicto.ok:
            return True
        mensaje = (
            "Hay horas parciales. ¿Sustituirlas por COMPLETO?"
            if solicitud.completo
            else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
        )
        if not self._confirm_conflicto(mensaje):
            return False
        try:
            if solicitud.completo:
                self._solicitud_use_cases.sustituir_por_completo(
                    persona_id, solicitud.fecha_pedida, solicitud
                )
            else:
                self._solicitud_use_cases.sustituir_por_parcial(
                    persona_id, solicitud.fecha_pedida, solicitud
                )
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return False
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error sustituyendo solicitud")
            QMessageBox.critical(self, "Error", str(exc))
            return False
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self.notas_input.setPlainText("")
        return False

    def _on_confirmar(self) -> None:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(self._pending_solicitudes)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF")
            QMessageBox.critical(self, "Error", str(exc))
            return
        default_path = str(Path.home() / default_name)
        pdf_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF",
            default_path,
            "PDF (*.pdf)",
        )
        if not pdf_path:
            return
        try:
            creadas, pendientes_restantes, errores, generado = (
                self._solicitud_use_cases.confirmar_lote_y_generar_pdf(
                    self._pending_solicitudes, Path(pdf_path)
                )
            )
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error confirmando solicitudes")
            QMessageBox.critical(self, "Error", str(exc))
            return
        if generado and self.abrir_pdf_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(generado)))
        if errores:
            QMessageBox.warning(self, "Errores", "\n".join(errores))
        self._pending_solicitudes = pendientes_restantes
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()

    def _on_generar_pdf_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        solicitudes = self.historico_model.solicitudes()
        if not solicitudes:
            QMessageBox.information(self, "Histórico", "No hay solicitudes para exportar.")
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(solicitudes)
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF histórico")
            QMessageBox.critical(self, "Error", str(exc))
            return
        default_path = str(Path.home() / default_name)
        pdf_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF histórico",
            default_path,
            "PDF (*.pdf)",
        )
        if not pdf_path:
            return
        try:
            generado = self._solicitud_use_cases.generar_pdf_historico(
                solicitudes, Path(pdf_path)
            )
        except (ValidacionError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error generando PDF histórico")
            QMessageBox.critical(self, "Error", str(exc))
            return
        if generado:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(generado)))

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
            resumen = self._solicitud_use_cases.calcular_resumen_saldos(persona.id or 0, filtro)
            pendientes_periodo = self._pending_minutes_for_period(filtro)
            pendientes_ano = self._pending_minutes_for_period(PeriodoFiltro.anual(filtro.year))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(resumen, pendientes_periodo, pendientes_ano)

    def _set_saldos_labels(
        self,
        resumen,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
    ) -> None:
        if resumen is None:
            texto = "Consumidas 00:00 / Bolsa 00:00 / Restantes 00:00"
            self._set_resumen_label(self.saldo_periodo_label, texto, False)
            self._set_resumen_label(self.saldo_anual_label, texto, False)
            self._set_resumen_label(self.saldo_global_label, texto, False)
            self._set_resumen_label(self.saldo_grupo_label, texto, False)
            return
        consumidas_periodo = resumen.individual.consumidas_periodo_min + pendientes_periodo
        bolsa_periodo = resumen.individual.bolsa_periodo_min
        restantes_periodo = bolsa_periodo - consumidas_periodo

        consumidas_anual = resumen.individual.consumidas_anual_min + pendientes_ano
        bolsa_anual = resumen.individual.bolsa_anual_min
        restantes_anual = bolsa_anual - consumidas_anual

        consumidas_global = resumen.global_anual.consumidas_anual_min + pendientes_ano
        bolsa_global = resumen.global_anual.bolsa_anual_min
        restantes_global = bolsa_global - consumidas_global

        consumidas_grupo = resumen.grupo_anual.consumidas_anual_min + pendientes_ano
        bolsa_grupo = resumen.grupo_anual.bolsa_anual_grupo_min
        restantes_grupo = bolsa_grupo - consumidas_grupo

        self._set_resumen_line(
            self.saldo_periodo_label, consumidas_periodo, bolsa_periodo, restantes_periodo
        )
        self._set_resumen_line(
            self.saldo_anual_label, consumidas_anual, bolsa_anual, restantes_anual
        )
        self._set_resumen_line(
            self.saldo_global_label, consumidas_global, bolsa_global, restantes_global
        )
        self._set_resumen_line(
            self.saldo_grupo_label, consumidas_grupo, bolsa_grupo, restantes_grupo
        )

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

    def _set_resumen_line(
        self, label: QLabel, consumidas: int, bolsa: int, restantes: int
    ) -> None:
        restantes_text, warning = self._format_restantes(restantes)
        texto = (
            f"Consumidas {self._format_minutes(consumidas)} / "
            f"Bolsa {self._format_minutes(bolsa)} / "
            f"{restantes_text}"
        )
        self._set_resumen_label(label, texto, warning)

    def _set_resumen_label(self, label: QLabel, texto: str, warning: bool) -> None:
        label.setText(texto)
        label.setProperty("role", "warning" if warning else "secondary")
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _format_restantes(self, minutos: int) -> tuple[str, bool]:
        if minutos < 0:
            return f"Exceso: {minutes_to_hhmm(abs(minutos))}", True
        return f"Restantes {self._format_minutes(minutos)}", False

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
