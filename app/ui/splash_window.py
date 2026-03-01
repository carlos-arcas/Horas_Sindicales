from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class SplashWindow(QWidget):
    def __init__(self, i18n: I18nManager) -> None:
        super().__init__()
        self._i18n = i18n
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

        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.t("splash_titulo"))
        self._cargando.setText(self._i18n.t("splash_cargando"))
