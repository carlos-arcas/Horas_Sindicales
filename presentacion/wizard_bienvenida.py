from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from presentacion.i18n import I18nManager


class WizardBienvenida(QDialog):
    TOTAL_PASOS = 4

    def __init__(self, i18n: I18nManager, obtener_ruta_guia_sync: ObtenerRutaGuiaSync, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._obtener_ruta_guia_sync = obtener_ruta_guia_sync
        self._stack = QStackedWidget()
        self._progress = QProgressBar()
        self._progress.setRange(1, self.TOTAL_PASOS)

        self._paso_titulo = QLabel()
        self._paso_texto = QLabel()
        self._paso_texto.setWordWrap(True)

        self._boton_ver_guia = QPushButton()
        self._boton_ver_guia.clicked.connect(self._abrir_guia_sync)

        self._check_pantalla_completa = QCheckBox()
        self._combo_idioma = QComboBox()
        self._combo_idioma.addItem("Español", "es")
        self._combo_idioma.addItem("English", "en")

        self._botones = QDialogButtonBox()
        self._atras = self._botones.addButton("", QDialogButtonBox.ActionRole)
        self._siguiente = self._botones.addButton("", QDialogButtonBox.ActionRole)
        self._atras.clicked.connect(self._ir_atras)
        self._siguiente.clicked.connect(self._ir_siguiente)

        self._stack.addWidget(self._crear_paso("wizard_paso_1", "wizard_bienvenida_texto"))
        self._stack.addWidget(self._crear_paso("wizard_paso_2", "wizard_conceptos_texto"))
        self._stack.addWidget(self._crear_paso_sync())
        self._stack.addWidget(self._crear_paso_preferencias())

        layout = QVBoxLayout(self)
        layout.addWidget(self._progress)
        layout.addWidget(self._stack)
        layout.addWidget(self._botones)

        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._combo_idioma.currentIndexChanged.connect(self._idioma_cambiado_por_usuario)
        self._actualizar_textos()
        self._actualizar_estado_botones()

    @property
    def pantalla_completa_por_defecto(self) -> bool:
        return self._check_pantalla_completa.isChecked()

    @property
    def idioma_seleccionado(self) -> str:
        return str(self._combo_idioma.currentData())

    def _crear_paso(self, key_titulo: str, key_texto: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        titulo = QLabel(self._i18n.t(key_titulo))
        titulo.setProperty("role", "h3")
        texto = QLabel(self._i18n.t(key_texto))
        texto.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(texto)
        layout.addStretch(1)
        page.setProperty("i18n_titulo", key_titulo)
        page.setProperty("i18n_texto", key_texto)
        return page

    def _crear_paso_sync(self) -> QWidget:
        page = self._crear_paso("wizard_paso_3", "wizard_sync_texto")
        page.layout().addWidget(self._boton_ver_guia)
        return page

    def _crear_paso_preferencias(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        titulo = QLabel()
        titulo.setProperty("role", "h3")
        titulo.setProperty("i18n_titulo", "wizard_paso_4")
        layout.addWidget(titulo)
        layout.addWidget(self._check_pantalla_completa)
        self._label_idioma = QLabel()
        layout.addWidget(self._label_idioma)
        layout.addWidget(self._combo_idioma)
        layout.addStretch(1)
        return page

    def _actualizar_textos(self) -> None:
        self.setWindowTitle(self._i18n.t("wizard_titulo"))
        for i in range(self._stack.count()):
            page = self._stack.widget(i)
            key_titulo = page.property("i18n_titulo")
            key_texto = page.property("i18n_texto")
            labels = page.findChildren(QLabel)
            if key_titulo and labels:
                labels[0].setText(self._i18n.t(str(key_titulo)))
            if key_texto and len(labels) > 1:
                labels[1].setText(self._i18n.t(str(key_texto)))
        self._boton_ver_guia.setText(self._i18n.t("wizard_boton_ver_guia_sync"))
        self._check_pantalla_completa.setText(self._i18n.t("wizard_pref_fullscreen"))
        self._label_idioma.setText(self._i18n.t("wizard_pref_idioma"))
        self._actualizar_estado_botones()

    def _actualizar_estado_botones(self) -> None:
        current = self._stack.currentIndex() + 1
        self._progress.setValue(current)
        self._progress.setFormat(self._i18n.t("wizard_progreso", actual=current, total=self.TOTAL_PASOS))
        self._atras.setText(self._i18n.t("wizard_boton_atras"))
        if current == self.TOTAL_PASOS:
            self._siguiente.setText(self._i18n.t("wizard_boton_finalizar"))
        else:
            self._siguiente.setText(self._i18n.t("wizard_boton_siguiente"))
        self._atras.setEnabled(current > 1)

    def _ir_atras(self) -> None:
        self._stack.setCurrentIndex(max(0, self._stack.currentIndex() - 1))
        self._actualizar_estado_botones()

    def _ir_siguiente(self) -> None:
        if self._stack.currentIndex() >= self.TOTAL_PASOS - 1:
            self.accept()
            return
        self._stack.setCurrentIndex(self._stack.currentIndex() + 1)
        self._actualizar_estado_botones()

    def _idioma_cambiado_por_usuario(self) -> None:
        self._i18n.set_idioma(self.idioma_seleccionado)

    def _abrir_guia_sync(self) -> None:
        try:
            ruta = Path(self._obtener_ruta_guia_sync.ejecutar())
            contenido = ruta.read_text(encoding="utf-8")
            self._mostrar_dialogo_guia(contenido)
        except Exception:
            QMessageBox.warning(self, self._i18n.t("wizard_sync_dialog_titulo"), self._i18n.t("wizard_sync_dialog_error"))

    def _mostrar_dialogo_guia(self, markdown: str) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle(self._i18n.t("wizard_sync_dialog_titulo"))
        layout = QVBoxLayout(dialogo)
        visor = QTextBrowser(dialogo)
        # Se usa texto plano para mantener el Markdown fiel y evitar transformaciones visuales inesperadas.
        visor.setPlainText(markdown)
        layout.addWidget(visor)
        botonera = QDialogButtonBox(QDialogButtonBox.Close)
        botonera.rejected.connect(dialogo.reject)
        botonera.accepted.connect(dialogo.accept)
        layout.addWidget(botonera)
        dialogo.resize(760, 520)
        dialogo.exec()
