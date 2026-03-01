from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from app.ui.qt_hilos import assert_hilo_ui_o_log
from presentacion.i18n import I18nManager


logger = logging.getLogger(__name__)


class SplashWindow(QWidget):
    _status_requested = Signal(str)
    _close_requested = Signal()

    def __init__(self, i18n: I18nManager) -> None:
        super().__init__()
        assert_hilo_ui_o_log("SplashWindow.__init__", logger)
        self._i18n = i18n
        self._startup_thread: QThread | None = None
        self._startup_worker: QObject | None = None
        self._watchdog_timer: QObject | None = None
        self._close_in_progress = False
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(460, 200)

        self._logo = QLabel("🕒")
        self._logo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._logo.setProperty("role", "h2")

        self._titulo = QLabel()
        self._titulo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._titulo.setProperty("role", "h3")

        self._cargando = QLabel()
        self._cargando.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._progreso = QProgressBar()
        self._progreso.setTextVisible(False)
        self._progreso.setRange(0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(self._logo)
        layout.addWidget(self._titulo)
        layout.addWidget(self._cargando)
        layout.addWidget(self._progreso)

        self._estado_clave = "splash_cargando"
        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._status_requested.connect(self._set_status_internal, Qt.ConnectionType.QueuedConnection)
        self._close_requested.connect(self._request_close_internal, Qt.ConnectionType.QueuedConnection)
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.t("splash_titulo"))
        self._cargando.setText(self._i18n.t(self._estado_clave))

    @Slot(str)
    def _set_status_internal(self, texto: str) -> None:
        self._estado_clave = texto
        self._cargando.setText(self._i18n.t(texto))

    def set_status(self, texto: str) -> None:
        if QThread.currentThread() == self.thread():
            self._set_status_internal(texto)
            return
        self._status_requested.emit(texto)

    def registrar_arranque(self, hilo: QThread, worker: QObject) -> None:
        self._startup_thread = hilo
        self._startup_worker = worker

    def registrar_watchdog(self, timer: QObject) -> None:
        self._watchdog_timer = timer

    @Slot()
    def _request_close_internal(self) -> None:
        if self._close_in_progress:
            return
        self._close_in_progress = True
        self.hide()
        self.close()

    def request_close(self) -> None:
        if QThread.currentThread() == self.thread():
            self._request_close_internal()
            return
        self._close_requested.emit()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        hilo = self._startup_thread
        if hilo is not None and hilo.isRunning():
            hilo.quit()
            self._close_in_progress = False
            event.ignore()
            return
        super().closeEvent(event)
