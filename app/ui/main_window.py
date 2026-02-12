from __future__ import annotations

import logging
import json
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QDate, QSettings, QTime, QUrl, Qt, QObject, Signal, Slot, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QApplication,
    QAbstractItemView,
    QPlainTextEdit,
    QGridLayout,
    QFrame,
    QHeaderView,
    QProgressBar,
    QSizePolicy,
    QSpinBox,
    QScrollArea,
    QStatusBar,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.conflicts_service import ConflictsService
from app.application.dto import PeriodoFiltro, PersonaDTO, SolicitudDTO
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.domain.services import BusinessRuleError, ValidacionError
from app.domain.time_utils import minutes_to_hhmm
from app.domain.request_time import validate_request_inputs
from app.domain.sync_models import SyncSummary
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsConfigError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
)
from app.ui.models_qt import SolicitudesTableModel
from app.ui.dialog_opciones import OpcionesDialog
from app.ui.conflicts_dialog import ConflictsDialog
from app.ui.group_dialog import GrupoConfigDialog, PdfConfigDialog
from app.ui.person_dialog import PersonaDialog
from app.ui.style import apply_theme
from app.ui.widgets.header import HeaderWidget
from app.ui.widgets.toast import ToastManager

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    PDF_PREVIEW_AVAILABLE = True
except ImportError:  # pragma: no cover - depende de instalación local
    QPdfDocument = None
    QPdfView = None
    PDF_PREVIEW_AVAILABLE = False

logger = logging.getLogger(__name__)


class SyncWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.sync()
        except Exception as exc:
            logger.exception("Error durante la sincronización")
            self.failed.emit(
                {
                    "error": exc,
                    "details": traceback.format_exc(),
                }
            )
            return
        self.finished.emit(summary)


class PushWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.push()
        except Exception as exc:
            logger.exception("Error durante la subida")
            self.failed.emit(
                {
                    "error": exc,
                    "details": traceback.format_exc(),
                }
            )
            return
        self.finished.emit(summary)


class OptionalConfirmDialog(QDialog):
    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        text = QLabel(message)
        text.setWordWrap(True)
        layout.addWidget(text)

        self.skip_next_check = QCheckBox("No mostrar de nuevo")
        layout.addWidget(self.skip_next_check)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Aceptar")
        ok.setProperty("variant", "primary")
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        layout.addLayout(buttons)


class PdfPreviewDialog(QDialog):
    def __init__(self, pdf_generator, default_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pdf_generator = pdf_generator
        self._default_name = default_name
        self._last_pdf_path: Path | None = None
        self._pdf_document = None
        self.setWindowTitle("Previsualización PDF")
        self.resize(920, 680)
        self._build_ui()
        self._generate_preview()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.info_label = QLabel("Genera una vista previa antes de guardar.")
        self.info_label.setProperty("role", "secondary")
        layout.addWidget(self.info_label)

        if PDF_PREVIEW_AVAILABLE and QPdfView and QPdfDocument:
            self._pdf_document = QPdfDocument(self)
            self._pdf_view = QPdfView(self)
            self._pdf_view.setDocument(self._pdf_document)
            layout.addWidget(self._pdf_view, 1)
        else:
            self._pdf_view = QLabel(
                "QPdfView no está disponible en esta instalación.\n"
                "Se abrirá la vista previa con el visor del sistema."
            )
            self._pdf_view.setAlignment(Qt.AlignCenter)
            self._pdf_view.setWordWrap(True)
            self._pdf_view.setProperty("role", "secondary")
            layout.addWidget(self._pdf_view, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)

        refresh = QPushButton("Generar/Actualizar vista")
        refresh.setProperty("variant", "secondary")
        refresh.clicked.connect(self._generate_preview)
        actions.addWidget(refresh)

        save_as = QPushButton("Guardar como…")
        save_as.setProperty("variant", "primary")
        save_as.clicked.connect(self._save_as)
        actions.addWidget(save_as)

        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "secondary")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        layout.addLayout(actions)

    def _generate_preview(self) -> None:
        with NamedTemporaryFile(prefix="horas_sindicales_", suffix=".pdf", delete=False) as tmp:
            temp_path = Path(tmp.name)
        generated = self._pdf_generator(temp_path)
        self._last_pdf_path = generated
        self.info_label.setText(f"Vista previa lista: {generated.name}")
        if PDF_PREVIEW_AVAILABLE and self._pdf_document is not None:
            self._pdf_document.load(str(generated))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(generated)))

    def _save_as(self) -> None:
        if self._last_pdf_path is None:
            return
        default_path = str(Path.home() / self._default_name)
        target_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_path, "PDF (*.pdf)")
        if not target_path:
            return
        Path(target_path).write_bytes(self._last_pdf_path.read_bytes())
        self.accept()

    @property
    def exported_path(self) -> Path | None:
        return self._last_pdf_path


class MainWindow(QMainWindow):
    def __init__(
        self,
        persona_use_cases: PersonaUseCases,
        solicitud_use_cases: SolicitudUseCases,
        grupo_use_cases: GrupoConfigUseCases,
        sheets_service: SheetsService,
        sync_sheets_use_case: SyncSheetsUseCase,
        conflicts_service: ConflictsService,
    ) -> None:
        super().__init__()
        app = QApplication.instance()
        if app:
            apply_theme(app)
        self._persona_use_cases = persona_use_cases
        self._solicitud_use_cases = solicitud_use_cases
        self._grupo_use_cases = grupo_use_cases
        self._sheets_service = sheets_service
        self._sync_service = sync_sheets_use_case
        self._conflicts_service = conflicts_service
        self._settings = QSettings("HorasSindicales", "HorasSindicales")
        self._personas: list[PersonaDTO] = []
        self._pending_solicitudes: list[SolicitudDTO] = []
        self._sync_in_progress = False
        self.toast = ToastManager()
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self.toast.attach_to(self)
        self._load_personas()
        self._refresh_last_sync_label()
        self._update_sync_button_state()

    def _create_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", True)
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
        layout.setSpacing(14)

        header_frame = QFrame()
        header_frame.setProperty("role", "header")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_top = QHBoxLayout()
        header_top.setSpacing(12)
        header = HeaderWidget()
        header_top.addWidget(header, 1)

        header_actions = QHBoxLayout()
        header_actions.setSpacing(8)
        self.edit_grupo_button = QPushButton("Editar grupo")
        self.edit_grupo_button.setProperty("variant", "secondary")
        self.edit_grupo_button.clicked.connect(self._on_edit_grupo)
        header_actions.addWidget(self.edit_grupo_button)

        self.editar_pdf_button = QPushButton("Opciones (PDF)")
        self.editar_pdf_button.setProperty("variant", "secondary")
        self.editar_pdf_button.clicked.connect(self._on_edit_pdf)
        header_actions.addWidget(self.editar_pdf_button)

        self.opciones_button = QPushButton("Sincronización Google Sheets")
        self.opciones_button.setProperty("variant", "secondary")
        self.opciones_button.clicked.connect(self._on_open_opciones)
        header_actions.addWidget(self.opciones_button)
        header_top.setAlignment(header_actions, Qt.AlignTop | Qt.AlignRight)
        header_top.addLayout(header_actions)
        header_layout.addLayout(header_top)
        header_separator = QFrame()
        header_separator.setObjectName("headerSeparator")
        header_separator.setFixedHeight(3)
        header_layout.addWidget(header_separator)
        layout.addWidget(header_frame)

        self._content_row = QBoxLayout(QBoxLayout.LeftToRight)
        self._content_row.setSpacing(14)
        layout.addLayout(self._content_row, 1)

        left_column = QVBoxLayout()
        left_column.setSpacing(14)
        self._content_row.addLayout(left_column, 3)

        sync_card, sync_layout = self._create_card("Sincronización")
        sync_heading = QLabel("Google Sheets")
        sync_heading.setProperty("role", "sectionTitle")
        sync_layout.addWidget(sync_heading)
        sync_actions = QHBoxLayout()
        sync_actions.setSpacing(8)
        self.sync_button = QPushButton("Sincronizar")
        self.sync_button.setProperty("variant", "primary")
        self.sync_button.clicked.connect(self._on_sync)
        sync_actions.addWidget(self.sync_button)

        self.review_conflicts_button = QPushButton("Revisar discrepancias")
        self.review_conflicts_button.setProperty("variant", "secondary")
        self.review_conflicts_button.setEnabled(False)
        self.review_conflicts_button.clicked.connect(self._on_review_conflicts)
        sync_actions.addWidget(self.review_conflicts_button)
        sync_layout.addLayout(sync_actions)

        self.last_sync_label = QLabel("Última sync: --")
        self.last_sync_label.setProperty("role", "secondary")
        sync_layout.addWidget(self.last_sync_label)

        self.sync_status_label = QLabel("Sincronizando con Google Sheets…")
        self.sync_status_label.setProperty("role", "secondary")
        self.sync_status_label.setVisible(False)
        self.sync_progress = QProgressBar()
        self.sync_progress.setRange(0, 0)
        self.sync_progress.setTextVisible(False)
        self.sync_progress.setVisible(False)
        sync_status_row = QHBoxLayout()
        sync_status_row.setSpacing(8)
        sync_status_row.addWidget(self.sync_status_label)
        sync_status_row.addWidget(self.sync_progress, 1)
        sync_layout.addLayout(sync_status_row)
        persona_card, persona_layout = self._create_card("Delegado")

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
        persona_layout.addLayout(persona_actions)

        persona_selector = QHBoxLayout()
        persona_selector.setSpacing(8)
        persona_label = QLabel("Delegado")
        persona_label.setProperty("role", "sectionTitle")
        persona_selector.addWidget(persona_label)
        self.persona_combo = QComboBox()
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        persona_selector.addWidget(self.persona_combo, 1)
        persona_layout.addLayout(persona_selector)

        persona_delete = QHBoxLayout()
        self.delete_persona_button = QPushButton("Eliminar delegado")
        self.delete_persona_button.setProperty("variant", "danger")
        self.delete_persona_button.clicked.connect(self._on_delete_persona)
        persona_delete.addWidget(self.delete_persona_button)
        persona_delete.addStretch(1)
        persona_layout.addLayout(persona_delete)
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

        self.total_preview_label = QLabel("Total petición")
        self.total_preview_label.setProperty("role", "secondary")
        solicitud_row.addWidget(self.total_preview_label)

        self.total_preview_input = QLineEdit("00:00")
        self.total_preview_input.setReadOnly(True)
        self.total_preview_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_preview_input.setMaximumWidth(84)
        solicitud_row.addWidget(self.total_preview_input)

        self.cuadrante_warning_label = QLabel("")
        self.cuadrante_warning_label.setProperty("role", "secondary")
        self.cuadrante_warning_label.setVisible(False)
        solicitud_row.addWidget(self.cuadrante_warning_label)

        self.agregar_button = QPushButton("Agregar")
        self.agregar_button.setProperty("variant", "primary")
        self.agregar_button.clicked.connect(
            self._on_add_pendiente,
            Qt.ConnectionType.UniqueConnection,
        )
        solicitud_row.addWidget(self.agregar_button)
        solicitud_row.addStretch(1)
        solicitud_layout.addLayout(solicitud_row)

        self.solicitud_inline_error = QLabel("")
        self.solicitud_inline_error.setProperty("role", "error")
        self.solicitud_inline_error.setVisible(False)
        solicitud_layout.addWidget(self.solicitud_inline_error)

        notas_row = QHBoxLayout()
        notas_row.setSpacing(8)
        notas_row.addWidget(QLabel("Notas"))
        self.notas_input = QPlainTextEdit()
        self.notas_input.setPlaceholderText("Notas para la solicitud")
        self.notas_input.setMinimumHeight(74)
        self.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        notas_row.addWidget(self.notas_input, 1)
        solicitud_layout.addLayout(notas_row)
        left_column.addWidget(solicitud_card)

        pendientes_card, pendientes_layout = self._create_card("Pendientes de confirmar")
        self._pendientes_group = pendientes_card
        self.pendientes_table = QTableView()
        self.pendientes_model = SolicitudesTableModel([])
        self.pendientes_table.setModel(self.pendientes_model)
        self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pendientes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pendientes_table.setShowGrid(False)
        self.pendientes_table.setAlternatingRowColors(True)
        self.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pendientes_table.setMinimumHeight(240)
        self._configure_solicitudes_table(self.pendientes_table)
        pendientes_layout.addWidget(self.pendientes_table, 1)

        footer_separator = QFrame()
        footer_separator.setProperty("role", "subtleSeparator")
        footer_separator.setFixedHeight(1)
        pendientes_layout.addWidget(footer_separator)

        pendientes_footer = QHBoxLayout()
        pendientes_footer.setSpacing(10)

        left_actions = QHBoxLayout()
        left_actions.setSpacing(8)
        self.eliminar_pendiente_button = QPushButton("Eliminar selección")
        self.eliminar_pendiente_button.setProperty("variant", "danger")
        self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
        left_actions.addWidget(self.eliminar_pendiente_button)

        self.insertar_sin_pdf_button = QPushButton("Insertar sin generar PDF")
        self.insertar_sin_pdf_button.setProperty("variant", "secondary")
        self.insertar_sin_pdf_button.clicked.connect(self._on_insertar_sin_pdf)
        left_actions.addWidget(self.insertar_sin_pdf_button)
        pendientes_footer.addLayout(left_actions)

        pendientes_footer.addStretch(1)

        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)
        self.total_pendientes_label = QLabel("Total: 00:00")
        self.total_pendientes_label.setProperty("role", "sectionTitle")
        right_actions.addWidget(self.total_pendientes_label)

        self.abrir_pdf_check = QCheckBox("Abrir PDF")
        self.abrir_pdf_check.setChecked(True)
        right_actions.addWidget(self.abrir_pdf_check)

        self.confirmar_button = QPushButton("Confirmar y generar")
        self.confirmar_button.setProperty("variant", "primary")
        self.confirmar_button.clicked.connect(self._on_confirmar)
        right_actions.addWidget(self.confirmar_button)

        pendientes_footer.addLayout(right_actions)
        pendientes_layout.addLayout(pendientes_footer)
        left_column.addWidget(pendientes_card, 1)

        right_column = QVBoxLayout()
        right_column.setSpacing(14)
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

        self.saldo_periodo_consumidas = self._build_saldo_field()
        self.saldo_periodo_restantes = self._build_saldo_field()
        self.saldo_anual_consumidas = self._build_saldo_field()
        self.saldo_anual_restantes = self._build_saldo_field()
        self.saldo_grupo_consumidas = self._build_saldo_field()
        self.saldo_grupo_restantes = self._build_saldo_field()

        self.saldo_periodo_label = QLabel("Mensual")
        saldos_grid.addWidget(self.saldo_periodo_label, 1, 0)
        saldos_grid.addWidget(self.saldo_periodo_consumidas, 1, 1)
        saldos_grid.addWidget(self.saldo_periodo_restantes, 1, 2)

        saldos_grid.addWidget(QLabel("Anual delegada"), 2, 0)
        saldos_grid.addWidget(self.saldo_anual_consumidas, 2, 1)
        saldos_grid.addWidget(self.saldo_anual_restantes, 2, 2)

        saldos_grid.addWidget(QLabel("Anual grupo"), 3, 0)
        saldos_grid.addWidget(self.saldo_grupo_consumidas, 3, 1)
        saldos_grid.addWidget(self.saldo_grupo_restantes, 3, 2)
        saldos_layout.addLayout(saldos_grid)

        self.exceso_badge = QLabel("")
        self.exceso_badge.setProperty("role", "badge")
        self.exceso_badge.setVisible(False)
        exceso_row = QHBoxLayout()
        exceso_row.addStretch(1)
        exceso_row.addWidget(self.exceso_badge)
        saldos_layout.addLayout(exceso_row)

        bolsas_separator = QFrame()
        bolsas_separator.setProperty("role", "subtleSeparator")
        bolsas_separator.setFixedHeight(1)
        saldos_layout.addWidget(bolsas_separator)

        bolsas_grid = QGridLayout()
        bolsas_grid.setHorizontalSpacing(8)
        bolsas_grid.setVerticalSpacing(6)
        bolsas_grid.addWidget(QLabel("Bolsa mensual delegada"), 0, 0)
        self.bolsa_mensual_label = QLabel("00:00")
        self.bolsa_mensual_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_mensual_label, 0, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual delegada"), 1, 0)
        self.bolsa_delegada_label = QLabel("00:00")
        self.bolsa_delegada_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_delegada_label, 1, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual grupo"), 2, 0)
        self.bolsa_grupo_label = QLabel("00:00")
        self.bolsa_grupo_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_grupo_label, 2, 1)
        saldos_layout.addLayout(bolsas_grid)
        right_column.addWidget(saldos_card)

        historico_card, historico_layout = self._create_card("Histórico")
        self._historico_group = historico_card
        historico_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(10)
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

        self.historico_table = QTableView()
        self.historico_model = SolicitudesTableModel([])
        self.historico_table.setModel(self.historico_model)
        self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.historico_table.selectionModel().selectionChanged.connect(self._on_historico_selection_changed)
        self.historico_table.setShowGrid(False)
        self.historico_table.setAlternatingRowColors(True)
        self.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.historico_table.setMinimumHeight(260)
        self._configure_solicitudes_table(self.historico_table)
        historico_layout.addWidget(self.historico_table, 1)

        historico_actions = QHBoxLayout()
        historico_actions.setSpacing(10)
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
        right_column.addWidget(sync_card)

        self._scroll_area.setWidget(content)
        self.setCentralWidget(self._scroll_area)
        self._build_status_bar()

        self._normalize_input_heights()
        self._update_responsive_columns()
        self._configure_time_placeholders()
        self._on_period_mode_changed()
        self._update_solicitud_preview()
        self._update_action_state()

    def _build_status_bar(self) -> None:
        status = QStatusBar(self)
        status.setObjectName("mainStatusBar")
        self.setStatusBar(status)
        self.status_sync_label = QLabel("Sincronizando con Google Sheets…")
        self.status_sync_label.setVisible(False)
        self.status_sync_progress = QProgressBar()
        self.status_sync_progress.setRange(0, 0)
        self.status_sync_progress.setTextVisible(False)
        self.status_sync_progress.setVisible(False)
        self.status_pending_label = QLabel("Pendientes calculados: 00:00")
        status.addPermanentWidget(self.status_sync_label)
        status.addPermanentWidget(self.status_sync_progress)
        status.addPermanentWidget(self.status_pending_label)

    def _configure_solicitudes_table(self, table: QTableView) -> None:
        header = table.horizontalHeader()
        header.setMinimumSectionSize(78)
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setStretchLastSection(False)
        table.setColumnWidth(5, 240)
        table.verticalHeader().setDefaultSectionSize(30)
        table.verticalHeader().setVisible(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_responsive_columns()

    def _normalize_input_heights(self) -> None:
        controls = [
            self.persona_combo,
            self.fecha_input,
            self.desde_input,
            self.hasta_input,
            self.periodo_modo_combo,
            self.year_input,
            self.month_combo,
            self.add_persona_button,
            self.edit_persona_button,
            self.edit_grupo_button,
            self.opciones_button,
            self.delete_persona_button,
            self.agregar_button,
            self.eliminar_pendiente_button,
            self.editar_pdf_button,
            self.insertar_sin_pdf_button,
            self.confirmar_button,
            self.eliminar_button,
            self.generar_pdf_button,
        ]
        for control in controls:
            control.setMinimumHeight(34)

    def _update_responsive_columns(self) -> None:
        if not hasattr(self, "_content_row"):
            return
        available_width = self._scroll_area.viewport().width() if hasattr(self, "_scroll_area") else self.width()
        # En ventanas estrechas apilamos columnas para evitar recortes horizontales.
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
        self._update_solicitud_preview()

    def _configure_time_placeholders(self) -> None:
        self.desde_placeholder.setVisible(False)
        self.hasta_placeholder.setVisible(False)
        desde_hint = self.desde_container.sizeHint()
        hasta_hint = self.hasta_container.sizeHint()
        self.desde_placeholder.setFixedSize(desde_hint)
        self.hasta_placeholder.setFixedSize(hasta_hint)
        self._sync_completo_visibility(self.completo_check.isChecked())
        self._bind_manual_hours_preview_refresh()

    def _bind_manual_hours_preview_refresh(self) -> None:
        if not hasattr(self, "horas_input"):
            return
        horas_input = self.horas_input
        for signal_name in ("minutesChanged", "timeChanged", "valueChanged", "textChanged"):
            signal = getattr(horas_input, signal_name, None)
            if signal is None:
                continue
            try:
                signal.connect(self._update_solicitud_preview)
            except Exception:  # pragma: no cover - compatibilidad entre widgets Qt
                continue

    def _sync_completo_visibility(self, checked: bool) -> None:
        self.desde_input.setEnabled(not checked)
        self.hasta_input.setEnabled(not checked)
        self.desde_container.setToolTip("No aplica en solicitud completa" if checked else "")
        self.hasta_container.setToolTip("No aplica en solicitud completa" if checked else "")

    def _on_edit_grupo(self) -> None:
        dialog = GrupoConfigDialog(self._grupo_use_cases, self._sync_service, self)
        if dialog.exec():
            self._refresh_saldos()

    def _on_sync(self) -> None:
        if not self._sync_service.is_configured():
            self.toast.warning("No hay configuración de Google Sheets. Abre Opciones para configurarlo.", title="Sin configuración")
            return
        self._set_sync_in_progress(True)
        self._sync_thread = QThread()
        self._sync_worker = SyncWorker(self._sync_service)
        self._sync_worker.moveToThread(self._sync_thread)
        self._sync_thread.started.connect(self._sync_worker.run)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.failed.connect(self._on_sync_failed)
        self._sync_worker.finished.connect(self._sync_thread.quit)
        self._sync_worker.finished.connect(self._sync_worker.deleteLater)
        self._sync_thread.finished.connect(self._sync_thread.deleteLater)
        self._sync_thread.start()

    def _on_sync_finished(self, summary: SyncSummary) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        self._refresh_last_sync_label()
        self._show_sync_summary_dialog("Sincronización completada", summary)

    def _on_sync_failed(self, payload: object) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        error, details = self._normalize_sync_error(payload)
        self._show_sync_error_dialog(error, details)

    def _on_review_conflicts(self) -> None:
        dialog = ConflictsDialog(self._conflicts_service, self)
        dialog.exec()
        self.review_conflicts_button.setEnabled(self._conflicts_service.count_conflicts() > 0)

    def _on_open_opciones(self) -> None:
        dialog = OpcionesDialog(self._sheets_service, self)
        dialog.exec()
        self._update_sync_button_state()

    def _on_edit_pdf(self) -> None:
        dialog = PdfConfigDialog(self._grupo_use_cases, self._sync_service, self)
        dialog.exec()

    def _manual_hours_minutes(self) -> int:
        if not hasattr(self, "horas_input"):
            return 0
        horas_input = self.horas_input
        if hasattr(horas_input, "minutes"):
            return max(0, int(horas_input.minutes()))
        if hasattr(horas_input, "time"):
            qtime = horas_input.time()
            return (qtime.hour() * 60) + qtime.minute()
        if hasattr(horas_input, "value"):
            return max(0, int(horas_input.value() * 60))
        return 0

    def _build_preview_solicitud(self) -> SolicitudDTO | None:
        persona = self._current_persona()
        if persona is None:
            return None
        completo = self.completo_check.isChecked()
        fecha_pedida = self.fecha_input.date().toString("yyyy-MM-dd")
        desde = None if completo else self.desde_input.time().toString("HH:mm")
        hasta = None if completo else self.hasta_input.time().toString("HH:mm")
        manual_minutes = self._manual_hours_minutes()
        return SolicitudDTO(
            id=None,
            persona_id=persona.id or 0,
            fecha_solicitud=datetime.now().strftime("%Y-%m-%d"),
            fecha_pedida=fecha_pedida,
            desde=desde,
            hasta=hasta,
            completo=completo,
            horas=manual_minutes / 60 if manual_minutes > 0 else 0,
            observaciones=None,
            pdf_path=None,
            pdf_hash=None,
            notas=None,
        )

    def _calculate_preview_minutes(self) -> tuple[int | None, bool]:
        solicitud = self._build_preview_solicitud()
        if solicitud is None:
            return 0, False
        try:
            minutos = self._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
            return minutos, False
        except BusinessRuleError as exc:
            mensaje = str(exc).lower()
            warning = solicitud.completo and "configura el cuadrante" in mensaje
            return None, warning

    def _update_solicitud_preview(self) -> None:
        valid, message = self._validate_solicitud_form()
        minutos, warning = self._calculate_preview_minutes()
        total_txt = "—" if minutos is None or not valid else self._format_minutes(minutos)
        self.total_preview_input.setText(total_txt)
        self.cuadrante_warning_label.setVisible(warning)
        self.cuadrante_warning_label.setText("Cuadrante no configurado" if warning else "")
        self.solicitud_inline_error.setVisible(not valid)
        self.solicitud_inline_error.setText(message)
        self._update_action_state()

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        if self._current_persona() is None:
            return False, "Selecciona una persona para crear la solicitud."
        completo = self.completo_check.isChecked()
        errors = validate_request_inputs(
            None if completo else self.desde_input.time().toString("HH:mm"),
            None if completo else self.hasta_input.time().toString("HH:mm"),
            completo,
        )
        if errors:
            return False, next(iter(errors.values()))
        return True, ""

    def _update_action_state(self) -> None:
        persona_selected = self._current_persona() is not None
        form_valid, _ = self._validate_solicitud_form()
        self.agregar_button.setEnabled(persona_selected and form_valid)
        has_pending = bool(self._pending_solicitudes)
        self.insertar_sin_pdf_button.setEnabled(persona_selected and has_pending)
        self.confirmar_button.setEnabled(persona_selected and has_pending)
        self.edit_persona_button.setEnabled(persona_selected)
        self.delete_persona_button.setEnabled(persona_selected)
        self.edit_grupo_button.setEnabled(True)
        self.editar_pdf_button.setEnabled(True)
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
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error creando persona")
            self._show_critical_error(str(exc))
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
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error editando persona")
            self._show_critical_error(str(exc))
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
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error deshabilitando delegado")
            self._show_critical_error(str(exc))
            return
        self._load_personas()

    def _on_add_pendiente(self) -> None:
        logger.info("Botón Agregar pulsado en pantalla de Peticiones")
        solicitud = self._build_preview_solicitud()
        if solicitud is None:
            self.toast.warning("Selecciona una delegada antes de agregar una petición.", title="Validación")
            return

        try:
            minutos = self._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.error("Error calculando minutos de la petición", exc_info=True)
            self._show_critical_error(str(exc))
            return

        notas_text = self.notas_input.toPlainText().strip()
        solicitud = replace(
            solicitud,
            horas=self._solicitud_use_cases.minutes_to_hours_float(minutos),
            notas=notas_text or None,
        )
        logger.info(
            "Intentando insertar petición persona_id=%s fecha_pedida=%s completo=%s desde=%s hasta=%s horas=%s notas=%s",
            solicitud.persona_id,
            solicitud.fecha_pedida,
            solicitud.completo,
            solicitud.desde,
            solicitud.hasta,
            solicitud.horas,
            bool(solicitud.notas),
        )

        if not self._resolve_backend_conflict(solicitud.persona_id, solicitud):
            return

        try:
            creada, _ = self._solicitud_use_cases.agregar_solicitud(solicitud)
            self._pending_solicitudes.append(creada)
            self.pendientes_model.set_solicitudes(self._pending_solicitudes)
            self._update_pending_totals()
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.error("Error insertando petición en base de datos", exc_info=True)
            self._show_critical_error(str(exc))
            return

        self.notas_input.setPlainText("")
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self.toast.success("Petición agregada")

        visibles_ids = {item.id for item in self.historico_model.solicitudes() if item.id is not None}
        if creada.id is not None and creada.id not in visibles_ids:
            logger.info(
                "Petición creada con id=%s, pero no visible en histórico por filtros actuales.",
                creada.id,
            )
            self._show_optional_notice(
                "confirmaciones/no_visible_filtros",
                "Solicitud creada",
                "Se creó la solicitud, pero no se ve por los filtros activos del histórico.",
            )

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
            self.toast.warning(str(exc), title="Validación")
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
            self.toast.warning(str(exc), title="Validación")
            return False
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error sustituyendo solicitud")
            self._show_critical_error(str(exc))
            return False
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()
        self.notas_input.setPlainText("")
        return True

    def _on_insertar_sin_pdf(self) -> None:
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
                logger.exception("Error insertando solicitud sin PDF")
                errores.append(str(exc))
                pendientes_restantes.append(solicitud)

        if errores:
            self.toast.warning("\n".join(errores), title="Errores")
        if creadas:
            self.toast.success("Solicitudes insertadas sin generar PDF")

        self._pending_solicitudes = pendientes_restantes
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._update_pending_totals()
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()

    def _on_confirmar(self) -> None:
        persona = self._current_persona()
        if persona is None or not self._pending_solicitudes:
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf(self._pending_solicitudes)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF")
            self._show_critical_error(str(exc))
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
                self._solicitud_use_cases.confirmar_y_generar_pdf(
                    self._pending_solicitudes, Path(pdf_path)
                )
            )
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error confirmando solicitudes")
            self._show_critical_error(str(exc))
            return
        if generado and self.abrir_pdf_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(generado)))
        if errores:
            self.toast.warning("\n".join(errores), title="Errores")
        if generado and creadas:
            pdf_hash = creadas[0].pdf_hash
            fechas = [solicitud.fecha_pedida for solicitud in creadas]
            self._sync_service.register_pdf_log(persona.id or 0, fechas, pdf_hash)
            self._ask_push_after_pdf()
            self.toast.success("Exportación PDF OK")
        self._pending_solicitudes = pendientes_restantes
        self.pendientes_model.set_solicitudes(self._pending_solicitudes)
        self._update_pending_totals()
        self._refresh_historico()
        self._refresh_saldos()
        self._update_action_state()

    def _ask_push_after_pdf(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("PDF generado")
        dialog.setText("PDF generado. ¿Quieres subir los cambios a Google Sheets ahora?")
        subir_button = dialog.addButton("Subir ahora", QMessageBox.AcceptRole)
        dialog.addButton("Más tarde", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() != subir_button:
            return
        self._on_push_now()

    def _on_push_now(self) -> None:
        if not self._sync_service.is_configured():
            self.toast.warning("No hay configuración de Google Sheets. Abre Opciones para configurarlo.", title="Sin configuración")
            return
        self._set_sync_in_progress(True)
        self._sync_thread = QThread()
        self._sync_worker = PushWorker(self._sync_service)
        self._sync_worker.moveToThread(self._sync_thread)
        self._sync_thread.started.connect(self._sync_worker.run)
        self._sync_worker.finished.connect(self._on_push_finished)
        self._sync_worker.failed.connect(self._on_push_failed)
        self._sync_worker.finished.connect(self._sync_thread.quit)
        self._sync_worker.finished.connect(self._sync_worker.deleteLater)
        self._sync_thread.finished.connect(self._sync_thread.deleteLater)
        self._sync_thread.start()

    def _on_push_finished(self, summary: SyncSummary) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        if summary.conflicts > 0:
            dialog = ConflictsDialog(self._conflicts_service, self)
            dialog.exec()
        self._refresh_last_sync_label()
        self._show_sync_summary_dialog("Sincronización completada", summary)

    def _on_push_failed(self, payload: object) -> None:
        self._set_sync_in_progress(False)
        self._update_sync_button_state()
        error, details = self._normalize_sync_error(payload)
        self._show_sync_error_dialog(error, details)

    def _update_sync_button_state(self) -> None:
        configured = self._sync_service.is_configured()
        self.sync_button.setEnabled(configured and not self._sync_in_progress)
        self.review_conflicts_button.setEnabled(
            not self._sync_in_progress and self._conflicts_service.count_conflicts() > 0
        )

    def _show_sync_error_dialog(self, error: Exception, details: str | None) -> None:
        title = "Error de sincronización"
        icon = QMessageBox.Critical
        if isinstance(error, SheetsApiDisabledError):
            self._show_message_with_details(
                title,
                "La API de Google Sheets no está habilitada en tu proyecto de Google Cloud.\n\n"
                "Solución: entra en Google Cloud Console → APIs & Services → Library → "
                "Google Sheets API → Enable.\n\n"
                "Después espera 2–5 minutos y vuelve a probar.",
                details,
                icon,
            )
            return
        if isinstance(error, SheetsPermissionError):
            email = self._service_account_email()
            email_hint = f"{email}" if email else "la cuenta de servicio"
            self._show_message_with_details(
                title,
                "La hoja no está compartida con la cuenta de servicio.\n\n"
                f"Comparte la hoja con: {email_hint} como Editor.",
                details,
                icon,
            )
            return
        if isinstance(error, SheetsNotFoundError):
            self._show_message_with_details(
                title,
                "El Spreadsheet ID/URL no es válido o la hoja no existe.",
                details,
                icon,
            )
            return
        if isinstance(error, SheetsCredentialsError):
            self._show_message_with_details(
                title,
                "No se pueden leer las credenciales JSON seleccionadas.",
                details,
                icon,
            )
            return
        if isinstance(error, SheetsConfigError):
            self._show_message_with_details(
                title,
                "No hay configuración de Google Sheets. Abre Opciones para configurarlo.",
                details,
                QMessageBox.Warning,
            )
            return
        self._show_message_with_details(title, str(error), details, icon)

    def _show_sync_summary_dialog(self, title: str, summary: SyncSummary) -> None:
        last_sync = self._sync_service.get_last_sync_at()
        last_sync_text = self._format_timestamp(last_sync) if last_sync else "Nunca"
        omitted_duplicates = summary.omitted_duplicates
        errors = summary.conflicts
        message = (
            f"Subidas: {summary.uploaded}\n"
            f"Actualizadas: {summary.downloaded}\n"
            f"Omitidas por duplicado: {omitted_duplicates}\n"
            f"Errores: {errors}\n"
            f"Última sincronización: {last_sync_text}"
        )
        if errors > 0:
            self.toast.warning(message, title=title, duration_ms=7000)
        else:
            self.toast.success(message, title=title)

    def _show_message_with_details(
        self,
        title: str,
        message: str,
        details: str | None,
        icon: QMessageBox.Icon,
    ) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setIcon(icon)
        dialog.setText(message)
        details_button = None
        if details:
            details_button = dialog.addButton("Ver detalles", QMessageBox.ActionRole)
        dialog.addButton("Cerrar", QMessageBox.AcceptRole)
        dialog.exec()
        if details_button and dialog.clickedButton() == details_button:
            self._show_details_dialog(title, details)

    def _show_details_dialog(self, title: str, details: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        details_text = QPlainTextEdit()
        details_text.setReadOnly(True)
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
        dialog.resize(520, 360)
        dialog.exec()

    def _normalize_sync_error(self, payload: object) -> tuple[Exception, str | None]:
        if isinstance(payload, dict):
            error = payload.get("error")
            details = payload.get("details")
            if isinstance(error, Exception):
                return error, details
            return Exception(str(error)), details
        if isinstance(payload, Exception):
            return payload, None
        return Exception(str(payload)), None

    def _set_sync_in_progress(self, in_progress: bool) -> None:
        self._sync_in_progress = in_progress
        self.sync_status_label.setVisible(in_progress)
        self.sync_progress.setVisible(in_progress)
        self.status_sync_label.setVisible(in_progress)
        self.status_sync_progress.setVisible(in_progress)
        if in_progress:
            self.statusBar().showMessage("Sincronizando con Google Sheets…")
            self.sync_button.setEnabled(False)
            self.review_conflicts_button.setEnabled(False)
        else:
            self.statusBar().clearMessage()

    def _show_critical_error(self, message: str) -> None:
        self.toast.error(message, title="Error")
        QMessageBox.critical(self, "Error", message)

    def _show_optional_notice(self, key: str, title: str, message: str) -> None:
        if bool(self._settings.value(key, False, type=bool)):
            self.toast.info(message, title=title)
            return
        dialog = OptionalConfirmDialog(title, message, self)
        dialog.exec()
        if dialog.skip_next_check.isChecked():
            self._settings.setValue(key, True)
        self.toast.info(message, title=title)

    def _update_pending_totals(self) -> None:
        persona = self._current_persona()
        total_min = 0
        if persona is not None and self._pending_solicitudes:
            try:
                total_min = self._solicitud_use_cases.sumar_pendientes_min(persona.id or 0, self._pending_solicitudes)
            except BusinessRuleError:
                total_min = 0
        formatted = self._format_minutes(total_min)
        self.total_pendientes_label.setText(f"Total: {formatted}")
        self.status_pending_label.setText(f"Pendientes calculados: {formatted}")
        self.statusBar().showMessage(f"Pendientes calculados: {formatted}", 4000)

    def _service_account_email(self) -> str | None:
        config = self._sheets_service.get_config()
        if not config or not config.credentials_path:
            return None
        try:
            payload = json.loads(Path(config.credentials_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return str(payload.get("client_email", "")).strip() or None

    def _on_generar_pdf_historico(self) -> None:
        persona = self._current_persona()
        if persona is None:
            return
        filtro = self._current_periodo_filtro()
        if self.historico_model.rowCount() == 0:
            self.toast.info("No hay solicitudes para exportar.", title="Histórico")
            return
        try:
            default_name = self._solicitud_use_cases.sugerir_nombre_pdf_historico(filtro)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error preparando PDF histórico")
            self._show_critical_error(str(exc))
            return
        def _generate_preview(target: Path) -> Path:
            return self._solicitud_use_cases.exportar_historico_pdf(persona.id or 0, filtro, target)

        try:
            preview = PdfPreviewDialog(_generate_preview, default_name, self)
            result = preview.exec()
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error generando previsualización de PDF histórico")
            self._show_critical_error(str(exc))
            return
        if result == QDialog.DialogCode.Accepted:
            self._show_optional_notice(
                "confirmaciones/export_pdf_ok",
                "Exportación",
                "Exportación PDF OK",
            )

    def _on_eliminar(self) -> None:
        solicitud = self._selected_historico()
        if solicitud is None or solicitud.id is None:
            return
        try:
            self._solicitud_use_cases.eliminar_solicitud(solicitud.id)
        except (ValidacionError, BusinessRuleError) as exc:
            self.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error eliminando solicitud")
            self._show_critical_error(str(exc))
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
        self._update_pending_totals()
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
        self._update_periodo_label()
        persona = self._current_persona()
        if persona is None:
            self._set_saldos_labels(None)
            return
        try:
            resumen = self._solicitud_use_cases.calcular_resumen_saldos(persona.id or 0, filtro)
        except BusinessRuleError as exc:
            self.toast.warning(str(exc), title="Validación")
            self._set_saldos_labels(None)
            return
        self._set_saldos_labels(resumen)

    def _update_periodo_label(self) -> None:
        self.saldo_periodo_label.setText("Mensual")

    def _set_saldos_labels(
        self,
        resumen,
        pendientes_periodo: int = 0,
        pendientes_ano: int = 0,
    ) -> None:
        if resumen is None:
            self._set_saldo_line(self.saldo_periodo_consumidas, self.saldo_periodo_restantes, 0, 0)
            self._set_saldo_line(self.saldo_anual_consumidas, self.saldo_anual_restantes, 0, 0)
            self._set_saldo_line(self.saldo_grupo_consumidas, self.saldo_grupo_restantes, 0, 0)
            self._set_bolsa_labels(0, 0, 0)
            self.exceso_badge.setVisible(False)
            return
        consumidas_periodo = resumen.individual.consumidas_periodo_min
        bolsa_periodo = resumen.individual.bolsa_periodo_min
        restantes_periodo = bolsa_periodo - consumidas_periodo

        consumidas_anual = resumen.individual.consumidas_anual_min
        bolsa_anual = resumen.individual.bolsa_anual_min
        restantes_anual = bolsa_anual - consumidas_anual

        consumidas_grupo = resumen.grupo_anual.consumidas_anual_min
        bolsa_grupo = resumen.grupo_anual.bolsa_anual_grupo_min
        restantes_grupo = bolsa_grupo - consumidas_grupo

        self._set_saldo_line(
            self.saldo_periodo_consumidas,
            self.saldo_periodo_restantes,
            consumidas_periodo,
            restantes_periodo,
        )
        self._set_saldo_line(
            self.saldo_anual_consumidas,
            self.saldo_anual_restantes,
            consumidas_anual,
            restantes_anual,
        )
        self._set_saldo_line(
            self.saldo_grupo_consumidas,
            self.saldo_grupo_restantes,
            consumidas_grupo,
            restantes_grupo,
        )
        self._set_bolsa_labels(bolsa_periodo, bolsa_anual, bolsa_grupo)

        exceso = min(restantes_periodo, restantes_anual, restantes_grupo)
        if exceso < 0:
            self.exceso_badge.setText(f"Exceso {self._format_minutes(abs(exceso))}")
            self.exceso_badge.setVisible(True)
        else:
            self.exceso_badge.setVisible(False)

    def _on_historico_selection_changed(self) -> None:
        self._update_action_state()

    def _current_periodo_filtro(self) -> PeriodoFiltro:
        year = self.year_input.value()
        modo = self.periodo_modo_combo.currentData()
        if modo == "ANUAL":
            return PeriodoFiltro.anual(year)
        return PeriodoFiltro.mensual(year, self.month_combo.currentData())

    def _current_saldo_filtro(self) -> PeriodoFiltro:
        periodo_base = self.fecha_input.date() if hasattr(self, "fecha_input") else QDate.currentDate()
        return PeriodoFiltro.mensual(periodo_base.year(), periodo_base.month())

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
        self._update_pending_totals()
        self._update_action_state()

    def _set_saldo_line(
        self,
        consumidas_field: QLineEdit,
        restantes_field: QLineEdit,
        consumidas: int,
        restantes: int,
    ) -> None:
        consumidas_field.setText(self._format_minutes(consumidas))
        restantes_text, warning = self._format_restantes(restantes)
        restantes_field.setText(restantes_text)
        self._set_warning_state(restantes_field, warning)

    def _set_warning_state(self, field: QLineEdit, warning: bool) -> None:
        field.setProperty("status", "warning" if warning else None)
        field.style().unpolish(field)
        field.style().polish(field)
        field.update()

    def _set_bolsa_labels(
        self, bolsa_mensual: int, bolsa_delegada: int, bolsa_grupo: int
    ) -> None:
        self.bolsa_mensual_label.setText(self._format_minutes(bolsa_mensual))
        self.bolsa_delegada_label.setText(self._format_minutes(bolsa_delegada))
        self.bolsa_grupo_label.setText(self._format_minutes(bolsa_grupo))

    def _format_restantes(self, minutos: int) -> tuple[str, bool]:
        if minutos < 0:
            return f"Exceso {minutes_to_hhmm(abs(minutos))}", True
        return self._format_minutes(minutos), False

    def _confirm_conflicto(self, mensaje: str) -> bool:
        return (
            QMessageBox.question(self, "Conflicto", mensaje, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )

    def _refresh_last_sync_label(self) -> None:
        last_sync = self._sync_service.get_last_sync_at()
        if not last_sync:
            self.last_sync_label.setText("Última sync: Nunca")
            return
        formatted = self._format_timestamp(last_sync)
        self.last_sync_label.setText(f"Última sync: {formatted}")

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")

    def _format_minutes(self, minutos: int) -> str:
        if minutos < 0:
            return f"-{minutes_to_hhmm(abs(minutos))}"
        return minutes_to_hhmm(minutos)
