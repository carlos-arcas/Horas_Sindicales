from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.bootstrap.logging import log_operational_error
from app.entrypoints.diagnostico_widgets import (
    debe_abortar_watchdog_por_ventana_visible,
    decidir_cerrar_splash,
    es_widget_splash,
    hay_ventana_visible_no_splash,
)
from app.ui.qt_safe import safe_call
from app.ui.qt_safe_ops import es_objeto_qt_valido, safe_hide

if TYPE_CHECKING:
    from app.entrypoints.arranque_nucleo import ResultadoArranqueCore

LOGGER = logging.getLogger(__name__)


def _detener_y_destruir_timer_seguro(*args, **kwargs) -> None:
    from app.ui.qt_hilos import detener_y_destruir_timer_seguro

    detener_y_destruir_timer_seguro(*args, **kwargs)


def _es_objeto_qt_valido(objeto) -> bool:
    try:
        import shiboken6

        return bool(
            objeto is not None
            and shiboken6.isValid(objeto)
            and es_objeto_qt_valido(objeto)
        )
    except Exception:
        return es_objeto_qt_valido(objeto)


def _cerrar_splash_seguro(splash) -> None:
    safe_hide(splash)


def _stop_watchdog_en_main_thread(watchdog_timer) -> None:
    if watchdog_timer is None or not hasattr(watchdog_timer, "stop"):
        return
    if not _es_objeto_qt_valido(watchdog_timer):
        return
    try:
        from PySide6.QtCore import QTimer
    except Exception:
        try:
            watchdog_timer.stop()
        except RuntimeError:
            return
        return
    try:
        QTimer.singleShot(0, watchdog_timer.stop)
    except RuntimeError:
        return


def _dump_top_level_widgets(self, tag: str) -> None:
    info_widgets = self._obtener_info_top_level_widgets()
    LOGGER.info(
        "STARTUP_TOP_LEVEL_WIDGETS",
        extra={"extra": {"tag": tag, "widgets": info_widgets}},
    )


def _reintentar_mostrar_ventanas_principales(self) -> None:
    for widget in (self.wizard, self.main_window):
        if not _es_objeto_qt_valido(widget):
            continue
        safe_call(widget, "show")
        safe_call(widget, "raise_")
        safe_call(widget, "activateWindow")


def _mostrar_fallback_arranque(self) -> None:
    self._boot_finalizado = True
    self.terminado = True
    self._detener_watchdog_transicion()
    self._detener_watchdog_idempotente()
    self._marcar_boot_stage("fallback_show_begin")
    self._cerrar_splash_si_visible()
    if _es_objeto_qt_valido(self._fallback_window):
        safe_call(self._fallback_window, "show")
        safe_call(self._fallback_window, "raise_")
        safe_call(self._fallback_window, "activateWindow")
        self._marcar_boot_stage("fallback_shown")
        return

    from PySide6.QtWidgets import QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

    ventana = QMainWindow()
    ventana.setWindowTitle(self.i18n.t("startup_fallback_titulo"))
    raiz = QWidget(ventana)
    layout = QVBoxLayout(raiz)
    layout.addWidget(QLabel(self.i18n.t("startup_fallback_mensaje"), raiz))
    layout.addWidget(
        QLabel(self.i18n.t("startup_last_stage", etapa=self.ultima_etapa), raiz)
    )
    boton_reintentar = QPushButton(self.i18n.t("startup_fallback_reintentar"), raiz)
    boton_reintentar.clicked.connect(self._reintentar_mostrar_ventanas_principales)
    layout.addWidget(boton_reintentar)
    boton_salir = QPushButton(self.i18n.t("startup_fallback_salir"), raiz)
    boton_salir.clicked.connect(lambda: self.app.exit(2))
    layout.addWidget(boton_salir)
    ventana.setCentralWidget(raiz)
    self._fallback_window = ventana
    self.app.setProperty("_startup_fallback_window_ref", ventana)
    self._marcar_boot_stage("fallback_window_created")
    safe_call(ventana, "show")
    safe_call(ventana, "raise_")
    safe_call(ventana, "activateWindow")
    self._marcar_boot_stage("fallback_window_shown")
    self._marcar_boot_stage("fallback_shown")


def _registrar_etapa_terminal(self, stage: str) -> None:
    if self._etapa_terminal_mostrada:
        return
    self._etapa_terminal_mostrada = True
    self._marcar_boot_stage(stage)
    self._cancelar_watchdog_transicion()


def _cancelar_watchdog_transicion(self) -> None:
    if self._watchdog_transicion is None:
        return
    _detener_y_destruir_timer_seguro(
        self._watchdog_transicion,
        nombre="watchdog_transicion",
        logger=LOGGER,
        marcar_stage=self._marcar_boot_stage,
    )
    self._watchdog_transicion = None


def _armar_watchdog_transicion(self) -> None:
    from app.ui.qt_compat import QTimer
    from app.ui.qt_hilos import asegurar_en_hilo_ui

    asegurar_en_hilo_ui("_armar_watchdog_transicion")

    self._cancelar_watchdog_transicion()
    timer = QTimer(self.app)
    timer.setSingleShot(True)
    timer.setInterval(3000)

    def _on_timeout() -> None:
        if self._etapa_terminal_mostrada:
            return
        info_widgets = self._obtener_info_top_level_widgets()
        hay_visible_no_splash = hay_ventana_visible_no_splash(info_widgets)
        if debe_abortar_watchdog_por_ventana_visible(
            hay_visible_no_splash
        ) or self._hay_ventana_principal_visible():
            LOGGER.warning(
                "STARTUP_WATCHDOG_ABORTADO_POR_VENTANA_VISIBLE",
                extra={"extra": {"widgets": info_widgets, "hay_visible_no_splash": hay_visible_no_splash}},
            )
            return
        self._dump_top_level_widgets("watchdog_before_fallback")
        self._marcar_boot_stage("watchdog_triggered")
        self._cerrar_splash_si_visible()
        self._mostrar_fallback_arranque()

    timer.timeout.connect(_on_timeout)
    timer.start()
    self._watchdog_transicion = timer


def _activar_guardia_ventana_visible(self) -> None:
    if self._guardia_ventana_visible_disparada:
        return
    self._guardia_ventana_visible_disparada = True
    from app.ui.qt_compat import QTimer

    def _validar_ventana_visible() -> None:
        if self._hay_ventana_principal_visible():
            return
        self._marcar_boot_stage("ui_no_window_visible_timeout")
        log_operational_error(
            LOGGER,
            "STARTUP_UI_NO_VISIBLE_WINDOW",
            extra={"timeout_ms": 100},
        )
        self._mostrar_fallback_arranque()

    QTimer.singleShot(0, _validar_ventana_visible)
    QTimer.singleShot(100, _validar_ventana_visible)


def _detener_watchdog_idempotente(self) -> None:
    if self.watchdog_timer is None:
        return
    _detener_y_destruir_timer_seguro(
        self.watchdog_timer,
        nombre="watchdog_arranque",
        logger=LOGGER,
        marcar_stage=self._marcar_boot_stage,
    )
    if not self._watchdog_detenido:
        self._watchdog_detenido = True
    self.watchdog_timer = None
    self._timer_watchdog = None


def _cerrar_splash_idempotente(self) -> None:
    if self._splash_cerrado:
        return
    if not _es_objeto_qt_valido(self.splash):
        self._splash_cerrado = True
        return
    splash = self.splash
    self._marcar_boot_stage("splash_close_begin")
    safe_hide(splash)
    if hasattr(splash, "deleteLater"):
        safe_call(splash, "deleteLater")
    self.splash = None
    self._splash_cerrado = True
    self.app._startup_splash_closed = True
    self._marcar_boot_stage("splash_closed")
    self.app.processEvents()


def _cerrar_splash_si_visible(self) -> None:
    if not decidir_cerrar_splash(al_mostrar_fallback=True):
        return
    self._marcar_boot_stage("splash_close_attempt")
    splash_cerrados = 0

    if _es_objeto_qt_valido(self.splash):
        safe_call(self.splash, "hide")
        safe_call(self.splash, "close")
        visible = bool(safe_call(self.splash, "isVisible") or False)
        if not visible:
            splash_cerrados += 1
        self._cerrar_splash_idempotente()

    if hasattr(self.app, "topLevelWidgets"):
        try:
            top_level_widgets = list(self.app.topLevelWidgets())
        except Exception:  # noqa: BLE001
            top_level_widgets = []
        for widget in top_level_widgets:
            info_widget = {
                "clase": widget.__class__.__name__,
                "object_name": safe_call(widget, "objectName") or "",
            }
            if not es_widget_splash(info_widget):
                continue
            safe_call(widget, "hide")
            safe_call(widget, "close")
            splash_cerrados += 1

    LOGGER.info(
        "startup_splash_close_result",
        extra={"extra": {"splash_cerrados": splash_cerrados}},
    )
    self._dump_top_level_widgets("after_close_splash")
    self._marcar_boot_stage("splash_close_done")


def finalizar_arranque_interfaz(self, startup_payload: ResultadoArranqueCore) -> None:
    self._marcar_boot_stage("finalize_enter")
    if self._boot_timeout_disparado or self._boot_finalizado:
        LOGGER.warning(
            "UI_STARTUP_FINALIZE_GUARD_ABORT",
            extra={
                "extra": {
                    "boot_timeout_disparado": self._boot_timeout_disparado,
                    "boot_finalizado": self._boot_finalizado,
                    "ultima_etapa": self.ultima_etapa,
                }
            },
        )
        self._marcar_boot_stage("finalize_guard_abort")
        self._mostrar_fallback_arranque()
        return
    self._marcar_boot_stage("finalize_pipeline_begin")
    if self._finalizar_arranque_pipeline(startup_payload):
        self._marcar_boot_stage("finalize_pipeline_end")


def _finalizar_splash_con_ventana_principal(self, ventana_principal) -> None:
    if not _es_objeto_qt_valido(self.splash):
        return
    splash = self.splash
    if _es_objeto_qt_valido(ventana_principal) and hasattr(splash, "finish"):
        safe_call(splash, "finish", ventana_principal)
    self._marcar_boot_stage("splash_finish_called")
    safe_call(splash, "close")
    if _es_objeto_qt_valido(splash):
        visible = bool(safe_call(splash, "isVisible") or False)
        if visible:
            LOGGER.warning("splash_still_visible_after_finish")
    self._cerrar_splash_idempotente()


def _cerrar_splash_con_ventana(self, ventana) -> None:
    self._finalizar_splash_con_ventana_principal(ventana)


def _detener_watchdog_transicion(self) -> None:
    self._cancelar_watchdog_transicion()


def aplicar_ayudantes_arranque_a_coordinador(clase_coordinador) -> None:
    clase_coordinador._dump_top_level_widgets = _dump_top_level_widgets
    clase_coordinador._reintentar_mostrar_ventanas_principales = _reintentar_mostrar_ventanas_principales
    clase_coordinador._mostrar_fallback_arranque = _mostrar_fallback_arranque
    clase_coordinador._registrar_etapa_terminal = _registrar_etapa_terminal
    clase_coordinador._cancelar_watchdog_transicion = _cancelar_watchdog_transicion
    clase_coordinador._armar_watchdog_transicion = _armar_watchdog_transicion
    clase_coordinador._activar_guardia_ventana_visible = _activar_guardia_ventana_visible
    clase_coordinador._detener_watchdog_idempotente = _detener_watchdog_idempotente
    clase_coordinador._cerrar_splash_idempotente = _cerrar_splash_idempotente
    clase_coordinador._cerrar_splash_si_visible = _cerrar_splash_si_visible
    clase_coordinador.finalizar_arranque_interfaz = finalizar_arranque_interfaz
    clase_coordinador._finalizar_splash_con_ventana_principal = _finalizar_splash_con_ventana_principal
    clase_coordinador._cerrar_splash_con_ventana = _cerrar_splash_con_ventana
    clase_coordinador._detener_watchdog_transicion = _detener_watchdog_transicion
