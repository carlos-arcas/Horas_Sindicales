from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class PaginaPreferencias(QWidget):
    def __init__(self, i18n: I18nManager, idioma_actual: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        self._titulo = QLabel()
        self._titulo.setProperty("role", "h3")
        self._check_pantalla_completa = QCheckBox()
        self._label_idioma = QLabel()
        self._combo_idioma = QComboBox()

        layout = QVBoxLayout(self)
        layout.addWidget(self._titulo)
        layout.addWidget(self._check_pantalla_completa)
        layout.addWidget(self._label_idioma)
        layout.addWidget(self._combo_idioma)
        layout.addStretch(1)

        self._cargar_idiomas()
        self.seleccionar_idioma(idioma_actual)
        self.actualizar_textos()

    @property
    def check_pantalla_completa(self) -> QCheckBox:
        return self._check_pantalla_completa

    @property
    def combo_idioma(self) -> QComboBox:
        return self._combo_idioma

    def idioma_seleccionado(self) -> str:
        return str(self._combo_idioma.currentData())

    def seleccionar_idioma(self, idioma: str) -> None:
        index = self._combo_idioma.findData(idioma)
        self._combo_idioma.setCurrentIndex(index if index >= 0 else 0)

    def actualizar_textos(self) -> None:
        self._titulo.setText(self._i18n.t("wizard_paso_4"))
        self._check_pantalla_completa.setText(self._i18n.t("wizard_pref_fullscreen"))
        self._label_idioma.setText(self._i18n.t("wizard_pref_idioma"))
        idioma_anterior = self.idioma_seleccionado()
        self._combo_idioma.clear()
        self._cargar_idiomas()
        self.seleccionar_idioma(idioma_anterior)

    def _cargar_idiomas(self) -> None:
        self._combo_idioma.addItem(self._i18n.t("wizard_idioma_es"), "es")
        self._combo_idioma.addItem(self._i18n.t("wizard_idioma_en"), "en")
