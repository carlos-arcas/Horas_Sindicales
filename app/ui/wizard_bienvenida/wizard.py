from __future__ import annotations

from pathlib import Path
import logging

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QProgressBar, QStackedWidget, QVBoxLayout, QWidget

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from app.ui.wizard_bienvenida.paginas.pagina_basicos import PaginaBasicos
from app.ui.wizard_bienvenida.paginas.pagina_bienvenida import PaginaBienvenida
from app.ui.wizard_bienvenida.paginas.pagina_preferencias import PaginaPreferencias
from app.ui.wizard_bienvenida.paginas.pagina_sync import PaginaSync
from app.ui.qt_hilos import assert_hilo_ui_o_log
from app.ui.wizard_bienvenida.visor_guia_sync import VisorGuiaSyncDialog
from presentacion.i18n import I18nManager


logger = logging.getLogger(__name__)


class WizardBienvenida(QDialog):
    TOTAL_PASOS = 4

    def __init__(
        self,
        i18n: I18nManager,
        obtener_ruta_guia_sync: ObtenerRutaGuiaSync,
        idioma_inicial: str,
        pantalla_completa_inicial: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        assert_hilo_ui_o_log("WizardBienvenida.__init__", logger)
        self._i18n = i18n
        self._obtener_ruta_guia_sync = obtener_ruta_guia_sync

        self._stack = QStackedWidget()
        self._progress = QProgressBar()
        self._progress.setRange(1, self.TOTAL_PASOS)
        self._paginas = self._crear_paginas(idioma_inicial, pantalla_completa_inicial)
        for pagina in self._paginas:
            self._stack.addWidget(pagina)

        self._botones = QDialogButtonBox()
        self._atras = self._botones.addButton("", QDialogButtonBox.ActionRole)
        self._siguiente = self._botones.addButton("", QDialogButtonBox.ActionRole)
        self._atras.clicked.connect(self._ir_atras)
        self._siguiente.clicked.connect(self._ir_siguiente)

        layout = QVBoxLayout(self)
        layout.addWidget(self._progress)
        layout.addWidget(self._stack)
        layout.addWidget(self._botones)

        self._i18n.idioma_cambiado.connect(self._actualizar_textos)
        self._pagina_preferencias.combo_idioma.currentIndexChanged.connect(self._idioma_cambiado_por_usuario)
        self._actualizar_textos()
        self._actualizar_estado_botones()

    @property
    def pantalla_completa_por_defecto(self) -> bool:
        return self._pagina_preferencias.check_pantalla_completa.isChecked()

    @property
    def idioma_seleccionado(self) -> str:
        return self._pagina_preferencias.idioma_seleccionado()

    def _crear_paginas(self, idioma_inicial: str, pantalla_completa_inicial: bool) -> list[QWidget]:
        self._pagina_preferencias = PaginaPreferencias(self._i18n, idioma_inicial)
        self._pagina_preferencias.check_pantalla_completa.setChecked(pantalla_completa_inicial)
        return [
            PaginaBienvenida(self._i18n),
            PaginaBasicos(self._i18n),
            PaginaSync(self._i18n, self._abrir_guia_sync),
            self._pagina_preferencias,
        ]

    def _actualizar_textos(self) -> None:
        self.setWindowTitle(self._i18n.t("wizard_titulo"))
        for pagina in self._paginas:
            if hasattr(pagina, "actualizar_textos"):
                pagina.actualizar_textos()
        self._actualizar_estado_botones()

    def _actualizar_estado_botones(self) -> None:
        current = self._stack.currentIndex() + 1
        self._progress.setValue(current)
        self._progress.setFormat(self._i18n.t("wizard_progreso", actual=current, total=self.TOTAL_PASOS))
        self._atras.setText(self._i18n.t("wizard_boton_atras"))
        self._atras.setEnabled(current > 1)
        key_siguiente = "wizard_boton_finalizar" if current == self.TOTAL_PASOS else "wizard_boton_siguiente"
        self._siguiente.setText(self._i18n.t(key_siguiente))

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
            dialogo = VisorGuiaSyncDialog(ruta.read_text(encoding="utf-8"), self._i18n, parent=self)
            dialogo.exec()
        except OSError:
            QMessageBox.warning(self, self._i18n.t("wizard_sync_dialog_titulo"), self._i18n.t("wizard_sync_dialog_error"))
