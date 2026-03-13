from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.patterns import apply_modal_behavior, build_modal_actions
from app.ui.components.saldos_card import SaldosCard
from app.ui.copy_catalog import copy_text
from app.ui.vistas.ui_helpers import abrir_archivo_local
from app.ui.vistas.builders.main_window_builders import (
    build_main_window_widgets,
    build_shell_layout,
    build_status_bar,
)

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    PDF_PREVIEW_AVAILABLE = True
except Exception:  # pragma: no cover - depende de instalación local
    QPdfDocument = None
    QPdfView = None
    PDF_PREVIEW_AVAILABLE = False


class OptionalConfirmDialog(QDialog):
    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        text = QLabel(message)
        text.setWordWrap(True)
        layout.addWidget(text)

        self.skip_next_check = QCheckBox(copy_text("ui.confirmacion.no_mostrar_mas"))
        layout.addWidget(self.skip_next_check)

        cancel_button = QPushButton(copy_text("ui.confirmacion.cancelar"))
        cancel_button.setProperty("variant", "ghost")
        cancel_button.clicked.connect(self.reject)
        ok = QPushButton(copy_text("ui.comun.aceptar"))
        ok.setProperty("variant", "primary")
        ok.clicked.connect(self.accept)
        layout.addLayout(build_modal_actions(cancel_button, ok))
        apply_modal_behavior(self, primary_button=ok)


class PdfPreviewDialog(QDialog):
    def __init__(self, pdf_generator, default_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pdf_generator = pdf_generator
        self._default_name = default_name
        self._last_pdf_path: Path | None = None
        self._pdf_document = None
        self.setWindowTitle(copy_text("ui.confirmacion.previsualizacion_pdf_titulo"))
        self.resize(920, 680)
        self._build_ui()
        self._generate_preview()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.info_label = QLabel(copy_text("ui.confirmacion.previsualizacion_pdf_descripcion"))
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

        refresh = QPushButton(copy_text("ui.confirmacion.generar_actualizar_vista"))
        refresh.setProperty("variant", "secondary")
        refresh.clicked.connect(self._generate_preview)
        actions.addWidget(refresh)

        save_as = QPushButton(copy_text("ui.confirmacion.guardar_como"))
        save_as.setProperty("variant", "primary")
        save_as.clicked.connect(self._save_as)
        actions.addWidget(save_as)

        close_button = QPushButton(copy_text("ui.comun.cerrar"))
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(self.reject)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        apply_modal_behavior(self)

    def _generate_preview(self) -> None:
        with NamedTemporaryFile(prefix="horas_sindicales_", suffix=".pdf", delete=False) as tmp:
            temp_path = Path(tmp.name)
        generated = self._pdf_generator(temp_path)
        self._last_pdf_path = generated
        self.info_label.setText(copy_text("ui.confirmacion.vista_previa_lista", nombre=generated.name))
        if PDF_PREVIEW_AVAILABLE and self._pdf_document is not None:
            self._pdf_document.load(str(generated))
            return
        abrir_archivo_local(generated)

    def _save_as(self) -> None:
        if self._last_pdf_path is None:
            return
        default_path = str(Path.home() / self._default_name)
        target_path, _ = QFileDialog.getSaveFileName(self, copy_text("ui.confirmacion.guardar_pdf"), default_path, copy_text("ui.confirmacion.filtro_pdf"))
        if not target_path:
            return
        Path(target_path).write_bytes(self._last_pdf_path.read_bytes())
        self.accept()

    @property
    def exported_path(self) -> Path | None:
        return self._last_pdf_path


class HistoricoDetalleDialog(QDialog):
    def __init__(self, payload: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(copy_text("ui.historico.detalle_solicitud_titulo"))
        self.resize(560, 420)
        layout = QVBoxLayout(self)

        details = QTextEdit(self)
        details.setReadOnly(True)
        body = "\n".join(f"{key}: {value}" for key, value in payload.items())
        details.setPlainText(body)
        layout.addWidget(details, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        close_button = buttons.button(QDialogButtonBox.Close)
        assert close_button is not None, copy_text("ui.error_details.qdialog_close_missing")
        apply_modal_behavior(self, primary_button=close_button)


class SaldosDetalleDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(copy_text("ui.solicitudes.saldos"))
        self.resize(560, 460)
        layout = QVBoxLayout(self)

        saldos_card = SaldosCard(self)
        saldos_card.saldos_details_button.setChecked(True)
        saldos_card.saldos_details_button.setVisible(False)
        layout.addWidget(saldos_card, 1)

        if parent is not None and getattr(parent, "saldos_card", None) is not None:
            _copiar_estado_saldos(parent.saldos_card, saldos_card)

        close_button = QPushButton(copy_text("ui.comun.cerrar"))
        close_button.setProperty("variant", "primary")
        close_button.clicked.connect(self.accept)
        layout.addLayout(build_modal_actions(close_button))
        apply_modal_behavior(self, primary_button=close_button)


def _copiar_estado_saldos(origen: SaldosCard, destino: SaldosCard) -> None:
    destino.update_periodo_label(origen.saldo_periodo_label.text())
    for attr in (
        "saldo_periodo_consumidas",
        "saldo_periodo_restantes",
        "saldo_anual_consumidas",
        "saldo_anual_restantes",
        "saldo_grupo_consumidas",
        "saldo_grupo_restantes",
    ):
        getattr(destino, attr).setText(getattr(origen, attr).text())
    for attr in ("bolsa_mensual_label", "bolsa_delegada_label", "bolsa_grupo_label"):
        getattr(destino, attr).setText(getattr(origen, attr).text())
    destino.exceso_badge.setVisible(origen.exceso_badge.isVisible())
    destino.exceso_badge.setText(origen.exceso_badge.text())


def create_widgets(window) -> None:
    build_main_window_widgets(window)


def build_shell(window) -> None:
    build_shell_layout(window)


def build_status(window) -> None:
    build_status_bar(window)


def build_layout_phase(_window) -> None:
    """Fase explícita de layout preservada para compatibilidad."""


def apply_initial_state_phase(_window) -> None:
    """Fase explícita de estado inicial preservada para compatibilidad."""
