from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class PaginaTexto(QWidget):
    def __init__(
        self,
        i18n: I18nManager,
        key_titulo: str,
        key_texto: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._key_titulo = key_titulo
        self._key_texto = key_texto

        self._ui_construida = False
        self._construir_ui()

    def _construir_ui(self) -> None:
        if self._ui_construida:
            return

        self._titulo = QLabel()
        self._titulo.setProperty("role", "h3")
        self._texto = QLabel()
        self._texto.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._titulo)
        layout.addWidget(self._texto)
        layout.addStretch(1)

        self._ui_construida = True

    def actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.t(self._key_titulo))
        self._texto.setText(self._i18n.t(self._key_texto))

    def inicializar_textos(self) -> None:
        self.actualizar_textos()
