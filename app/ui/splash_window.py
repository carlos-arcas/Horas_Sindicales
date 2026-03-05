from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from app.ui.qt_hilos import assert_hilo_ui_o_log
from presentacion.i18n import I18nManager


logger = logging.getLogger(__name__)


def _es_qt_objeto_vivo(objeto: object | None) -> bool:
    if objeto is None:
        return False
    try:
        import shiboken6

        return bool(shiboken6.isValid(objeto))
    except Exception:
        return True


class SplashWindow(QWidget):
    _status_requested = Signal(str)
    _close_requested = Signal()

    def __init__(self, i18n: I18nManager) -> None:
        super().__init__()
        contexto_hilo = ".".join((type(self).__name__, self.__init__.__name__))
        assert_hilo_ui_o_log(contexto_hilo, logger)
        self._i18n = i18n
        self._startup_thread: QThread | None = None
        self._startup_worker: QObject | None = None
        self._watchdog_timer: QObject | None = None
        self._close_in_progress = False
        self._cierre_programatico = False
        self._cancelacion_emitida = False
        self._solicitar_cancelacion_arranque: Callable[[], None] | None = None
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

        self._estado_clave = "splash_window.cargando"
        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._status_requested.connect(self._set_status_internal, Qt.ConnectionType.QueuedConnection)
        self._close_requested.connect(self._request_close_internal, Qt.ConnectionType.QueuedConnection)
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.tr("splash_window.titulo"))
        self._cargando.setText(self._i18n.tr(self._estado_clave))

    @Slot(str)
    def _set_status_internal(self, texto: str) -> None:
        self._estado_clave = texto
        self._cargando.setText(self._i18n.tr(texto))

    def set_status(self, texto: str) -> None:
        if QThread.currentThread() == self.thread():
            self._set_status_internal(texto)
            return
        self._status_requested.emit(texto)

    def registrar_arranque(self, hilo: QThread, worker: QObject) -> None:
        self._startup_thread = hilo
        self._startup_worker = worker
        if hasattr(hilo, "destroyed"):
            hilo.destroyed.connect(self._on_startup_thread_destroyed)

    @Slot()
    def _on_startup_thread_destroyed(self) -> None:
        self._startup_thread = None

    def registrar_cancelacion_arranque(self, callback: Callable[[], None]) -> None:
        self._solicitar_cancelacion_arranque = callback

    def marcar_cierre_programatico(self) -> None:
        self._cierre_programatico = True

    def registrar_watchdog(self, timer: QObject) -> None:
        self._watchdog_timer = timer

    def _startup_running_seguro(self) -> bool:
        hilo = self._startup_thread
        if not _es_qt_objeto_vivo(hilo):
            return False
        try:
            return bool(hilo.isRunning())
        except RuntimeError:
            return False

    @Slot()
    def _request_close_internal(self) -> None:
        if self._close_in_progress:
            return
        self._close_in_progress = True
        self.marcar_cierre_programatico()
        self.hide()
        self.close()

    def request_close(self) -> None:
        if QThread.currentThread() == self.thread():
            self._request_close_internal()
            return
        self._close_requested.emit()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._cierre_programatico:
            logger.info("splash_close_programmatic", extra={"extra": {"BOOT_STAGE": "splash_close_programmatic"}})
            event.accept()
            super().closeEvent(event)
            return
        if not self._startup_running_seguro():
            event.accept()
            super().closeEvent(event)
            return
        if not self._cancelacion_emitida:
            self._cancelacion_emitida = True
            logger.info(
                "splash_close_requested_by_user",
                extra={"extra": {"BOOT_STAGE": "splash_close_requested_by_user"}},
            )
            try:
                if self._solicitar_cancelacion_arranque is not None:
                    self._solicitar_cancelacion_arranque()
            except RuntimeError:
                logger.warning("startup_cancel_request_runtime_error")
            except Exception:
                logger.exception("startup_cancel_request_failed")
            event.ignore()
            return
        super().closeEvent(event)
