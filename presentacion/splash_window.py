from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class SplashWindow(QWidget):
    def __init__(self, i18n: I18nManager) -> None:
        super().__init__()
        self._i18n = i18n
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(420, 180)

        self._titulo = QLabel()
        self._titulo.setProperty("role", "h3")
        self._subtitulo = QLabel()
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._titulo)
        layout.addWidget(self._subtitulo)
        layout.addWidget(self._progress)
        layout.addStretch(1)

        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.tr("splash_window.titulo"))
        self._subtitulo.setText(self._i18n.tr("splash_window.subtitulo"))
