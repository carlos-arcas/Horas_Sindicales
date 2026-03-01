from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class SplashWindow(QWidget):
    def __init__(self, i18n: I18nManager) -> None:
        super().__init__()
        self._i18n = i18n
        self._hilo_arranque: QThread | None = None
        self._worker_arranque: QObject | None = None
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
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.t("splash_titulo"))
        self._cargando.setText(self._i18n.t(self._estado_clave))

    def set_status(self, texto: str) -> None:
        self._estado_clave = texto
        self._cargando.setText(self._i18n.t(texto))

    def registrar_arranque(self, hilo: QThread, worker: QObject) -> None:
        self._hilo_arranque = hilo
        self._worker_arranque = worker

    def closeEvent(self, event) -> None:  # type: ignore[override]
        hilo = self._hilo_arranque
        if hilo is not None and hilo.isRunning():
            hilo.quit()
            event.ignore()
            return
        super().closeEvent(event)
