from __future__ import annotations

import logging
import traceback
import uuid
from types import TracebackType
from typing import Callable

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from aplicacion.casos_de_uso.idioma import GuardarIdiomaUI, ObtenerIdiomaUI
from aplicacion.casos_de_uso.onboarding import (
    MarcarOnboardingCompletado,
    ObtenerEstadoOnboarding,
    ReiniciarOnboarding,
)
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from app.application.use_cases.cargar_datos_demo_caso_uso import CargarDatosDemoCasoUso
from app.bootstrap.captura_fallos_fatales import (
    iniciar_captura_fallos_fatales,
    marcar_stage,
)
from app.bootstrap.exception_handler import manejar_excepcion_global
from app.bootstrap.logging import log_operational_error
from app.bootstrap.settings import project_root
from app.entrypoints.arranque_nucleo import ResultadoArranque
from app.entrypoints.post_show import preparar_mostrar_ventana, programar_post_init
from app.ui.qt_message_handler import instalar_qt_message_handler
from app.ui.qt_safe import safe_call
from app.ui.qt_safe_ops import es_objeto_qt_valido, safe_hide, safe_quit_thread

LOGGER = logging.getLogger(__name__)


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


class _CoordinadorArranqueConCierreDeterminista:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.startup_thread = self.thread
        self.main_window = None
        self.wizard = None
        self._quit_on_last_window_closed_previo = None
        self._quit_on_last_window_closed_restaurado = False
        self._guardia_ventana_visible_disparada = False
        self._fallback_window = None
        self._ultimo_startup_payload: ResultadoArranque | None = None
        self._cancelacion_arranque_solicitada = False
        self._cancelacion_arranque_completada = False
        self._etapa_terminal_mostrada = False
        self._watchdog_transicion = None
        self.ultima_etapa = ""

    def _marcar_boot_stage(self, stage: str) -> None:
        self.ultima_etapa = stage
        marcar_stage(stage)

    def solicitar_cancelacion_arranque_por_usuario(self) -> None:
        if self._cancelacion_arranque_completada:
            return
        if self._cancelacion_arranque_solicitada:
            return
        self._cancelacion_arranque_solicitada = True
        self._marcar_boot_stage("splash_close_requested_by_user")
        LOGGER.info(
            "startup_cancel_requested",
            extra={"extra": {"BOOT_STAGE": "startup_cancel_requested"}},
        )

        from app.ui.qt_compat import QTimer

        def _cancelar_en_ui() -> None:
            self._detener_watchdog_idempotente()
            self._solicitar_cierre_thread()
            self._cerrar_splash_idempotente()
            self._cancelacion_arranque_completada = True
            self._marcar_boot_stage("startup_cancel_done")
            LOGGER.info(
                "startup_cancel_done",
                extra={"extra": {"BOOT_STAGE": "startup_cancel_done"}},
            )
            self.app.exit(0)

        QTimer.singleShot(0, _cancelar_en_ui)

    def desactivar_quit_on_last_window_closed_temporalmente(self) -> None:
        if self._quit_on_last_window_closed_previo is not None:
            return
        valor_previo = self.app.quitOnLastWindowClosed()
        self._quit_on_last_window_closed_previo = bool(valor_previo)
        self.app.setQuitOnLastWindowClosed(False)
        self._marcar_boot_stage("quit_on_last_window_closed_temporal_false")

    def restaurar_quit_on_last_window_closed(self) -> None:
        if self._quit_on_last_window_closed_restaurado:
            return
        if self._quit_on_last_window_closed_previo is None:
            return
        self.app.setQuitOnLastWindowClosed(self._quit_on_last_window_closed_previo)
        self._quit_on_last_window_closed_restaurado = True
        self._marcar_boot_stage("quit_on_last_window_closed_restored")

    def _hay_ventana_principal_visible(self) -> bool:
        candidatos = [self.wizard, self.main_window]
        for widget in candidatos:
            if not _es_objeto_qt_valido(widget):
                continue
            try:
                if widget.isVisible():
                    return True
            except RuntimeError:
                continue
        return False

    def _reintentar_mostrar_ventanas_principales(self) -> None:
        for widget in (self.wizard, self.main_window):
            if not _es_objeto_qt_valido(widget):
                continue
            safe_call(widget, "show")
            safe_call(widget, "raise_")
            safe_call(widget, "activateWindow")

    def _mostrar_fallback_arranque(self) -> None:
        self._marcar_boot_stage("fallback_show_begin")
        if _es_objeto_qt_valido(self._fallback_window):
            safe_call(self._fallback_window, "show")
            safe_call(self._fallback_window, "raise_")
            safe_call(self._fallback_window, "activateWindow")
            self._marcar_boot_stage("fallback_shown")
            return

        from PySide6.QtWidgets import (
            QLabel,
            QMainWindow,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )

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
        if not _es_objeto_qt_valido(self._watchdog_transicion):
            return
        safe_call(self._watchdog_transicion, "stop")
        safe_call(self._watchdog_transicion, "deleteLater")
        self._watchdog_transicion = None

    def _armar_watchdog_transicion(self) -> None:
        from app.ui.qt_compat import QTimer

        self._cancelar_watchdog_transicion()
        timer = QTimer(self.app)
        timer.setSingleShot(True)
        timer.setInterval(3000)

        def _on_timeout() -> None:
            if self._etapa_terminal_mostrada:
                return
            if self._hay_ventana_principal_visible():
                return
            self._marcar_boot_stage("watchdog_triggered")
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
        if not _es_objeto_qt_valido(self.watchdog_timer):
            return
        try:
            _stop_watchdog_en_main_thread(self.watchdog_timer)
        except RuntimeError:
            return

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

    def on_finished(self, startup_payload: ResultadoArranque) -> None:
        self._marcar_boot_stage("on_finished_enter")
        self._marcar_boot_stage("worker_result_received_ok")
        self.terminado = True
        self._ultimo_startup_payload = startup_payload
        self._armar_watchdog_transicion()

        def _aplicar_resultado_en_ui() -> None:
            try:
                self._detener_watchdog_idempotente()
                self._solicitar_cierre_thread()
                try:
                    self._marcar_boot_stage("on_finished_before_resolver_container")
                    resolved_container = startup_payload.container
                    self._marcar_boot_stage("container_resolved_ok")
                    self._marcar_boot_stage("UI_CONTAINER_RESUELTO")
                    self._marcar_boot_stage("on_finished_after_resolver_container")
                except Exception:
                    self._marcar_boot_stage("container_resolved_error")
                    raise
                deps_arranque = startup_payload.deps_arranque
                deps_arranque = _actualizar_preferencias_en_hilo_ui(
                    resolved_container, deps_arranque
                )
                idioma = deps_arranque.obtener_idioma_ui.ejecutar()
                self.i18n.set_idioma(idioma)
                self._marcar_boot_stage("on_finished_before_close_splash")
                self._cerrar_splash_idempotente()
                self._marcar_boot_stage("on_finished_after_close_splash")
                orquestador = self.orquestador_factory(deps_arranque, self.i18n)
                requiere_wizard = not deps_arranque.obtener_estado_onboarding.ejecutar()
                self._marcar_boot_stage("decision_modo_arranque")
                LOGGER.info(
                    "STARTUP_MODE_DECISION",
                    extra={
                        "extra": {
                            "modo": "wizard" if requiere_wizard else "main",
                            "motivo": (
                                "onboarding_pendiente"
                                if requiere_wizard
                                else "onboarding_completado"
                            ),
                        }
                    },
                )
                if requiere_wizard:
                    self._marcar_boot_stage("on_finished_before_create_window")
                    self._marcar_boot_stage("wizard_create_start")
                    self._marcar_boot_stage("wizard_created")
                    self._marcar_boot_stage("wizard_show_scheduled")
                if not orquestador.resolver_onboarding():
                    self.app.exit(0)
                    return
                if requiere_wizard:
                    self._registrar_etapa_terminal("wizard_shown")
                    self._marcar_boot_stage("on_finished_after_create_window")

                self._marcar_boot_stage("on_finished_before_create_window")
                self._marcar_boot_stage("main_window_create_start")
                self.main_window = self.main_window_factory(
                    resolved_container,
                    deps_arranque,
                )
                window = self.main_window
                self._marcar_boot_stage("main_window_created")
                self._marcar_boot_stage("ui.mainwindow.construida")
                self._marcar_boot_stage("on_finished_after_create_window")
                self.app.setProperty("_main_window_ref", window)
                self.instalar_menu_ayuda(
                    window,
                    self.i18n,
                    ReiniciarOnboarding(resolved_container.repositorio_preferencias),
                    resolved_container.cargar_datos_demo_caso_uso,
                )
                from app.ui.qt_compat import QTimer

                def scheduler(fn: Callable[[], None]) -> None:
                    QTimer.singleShot(0, fn)

                def _mostrar_main_window() -> None:
                    try:
                        if orquestador.debe_iniciar_maximizada():
                            window.showMaximized()
                        else:
                            window.show()
                        safe_call(window, "raise_")
                        safe_call(window, "activateWindow")
                        self._registrar_etapa_terminal("main_window_shown")
                        self.app.processEvents()
                        self.restaurar_quit_on_last_window_closed()
                    except Exception as exc:  # noqa: BLE001
                        self._marcar_boot_stage("deferred_show_exception")
                        log_operational_error(
                            LOGGER,
                            "STARTUP_DEFERRED_SHOW_EXCEPTION",
                            exc=exc,
                            extra={"traceback": traceback.format_exc()},
                        )
                        self._mostrar_fallback_arranque()

                preparar_mostrar_ventana(
                    window=window,
                    splash=None,
                    scheduler=scheduler,
                    marcar_stage=marcar_stage,
                )
                self._marcar_boot_stage("main_window_show_scheduled")
                QTimer.singleShot(0, _mostrar_main_window)
                self._activar_guardia_ventana_visible()
                programar_post_init(
                    window=window,
                    scheduler=scheduler,
                    marcar_stage=marcar_stage,
                )
            except Exception as exc:  # noqa: BLE001
                self._marcar_boot_stage("on_finished_exception")
                log_operational_error(
                    LOGGER,
                    "STARTUP_ON_FINISHED_EXCEPTION",
                    exc=exc,
                    extra={
                        "traceback": traceback.format_exc(),
                        "ultima_etapa": self.ultima_etapa,
                    },
                )
                import sys

                self._reportar_fallo_arranque(
                    exc=exc,
                    trace_info=sys.exc_info(),
                    i18n=self.i18n,
                    splash=self.splash,
                    startup_thread=self.thread,
                    app=self.app,
                    watchdog_timer=self.watchdog_timer,
                )
                self._mostrar_fallback_arranque()

        try:
            _enqueue_on_ui_thread(self.app, _aplicar_resultado_en_ui)
        except Exception as exc:  # noqa: BLE001
            self._marcar_boot_stage("on_finished_exception")
            import sys

            self._reportar_fallo_arranque(
                exc=exc,
                trace_info=sys.exc_info(),
                i18n=self.i18n,
                splash=self.splash,
                startup_thread=self.thread,
                app=self.app,
                watchdog_timer=self.watchdog_timer,
            )
            self._mostrar_fallback_arranque()


def _enqueue_on_ui_thread(app, callback: Callable[[], None]) -> None:
    try:
        from PySide6.QtCore import QMetaObject, QObject, Qt, Slot

        class _Invocador(QObject):
            def __init__(self, fn: Callable[[], None]) -> None:
                super().__init__()
                self._fn = fn

            @Slot()
            def ejecutar(self) -> None:
                self._fn()

        invocador = _Invocador(callback)
        app.setProperty("_startup_ui_invocador", invocador)
        QMetaObject.invokeMethod(invocador, "ejecutar", Qt.QueuedConnection)
        return
    except Exception:
        callback()


def _resolver_startup_timeout_ms() -> int:
    import os

    raw = os.getenv("HORAS_STARTUP_TIMEOUT_MS", "25000")
    try:
        return max(1, int(raw))
    except ValueError:
        return 25_000


def construir_mensaje_error_ui(incident_id: str) -> str:
    return f"Ha ocurrido un error inesperado.\nID de incidente: {incident_id}"


def manejar_excepcion_ui(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> str:
    incident_id = manejar_excepcion_global(exc_type, exc_value, exc_traceback)
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance()
    if app is None:
        return incident_id
    try:
        QMessageBox.critical(
            None, "Error inesperado", construir_mensaje_error_ui(incident_id)
        )
    except Exception:
        pass
    return incident_id


def _resolver_incident_id(exc: Exception | None, trace_info) -> str:
    if trace_info is not None and all(trace_info):
        return manejar_excepcion_ui(trace_info[0], trace_info[1], trace_info[2])
    incident_id = f"INC-UI-{uuid.uuid4().hex[:12].upper()}"
    log_operational_error(
        LOGGER,
        "Fallo de arranque sin traceback tipado",
        exc=exc,
        extra={"incident_id": incident_id},
    )
    return incident_id


def _manejar_fallo_arranque(
    *,
    exc: Exception | None,
    trace_info,
    i18n,
    splash,
    startup_thread,
    app,
    dialogo_factory: Callable[..., object] | None = None,
    mensaje_usuario: str | None = None,
    incident_id: str | None = None,
    detalles: str | None = None,
    watchdog_timer=None,
) -> str:
    from PySide6.QtCore import QThread, QTimer, Qt
    from PySide6.QtWidgets import QApplication

    if getattr(app, "_fallo_arranque_en_progreso", False):
        return str(getattr(app, "_fallo_arranque_incident_id", "") or incident_id or "")

    app._fallo_arranque_en_progreso = True
    app._fallo_arranque_correlation_id = str(uuid.uuid4())
    resolved_incident_id = incident_id or _resolver_incident_id(exc, trace_info)
    app._fallo_arranque_incident_id = resolved_incident_id

    resolved_detalles = detalles or ""
    if not resolved_detalles:
        if trace_info is not None and all(trace_info):
            resolved_detalles = "".join(
                traceback.format_exception(trace_info[0], trace_info[1], trace_info[2])
            )
        elif exc is not None:
            resolved_detalles = repr(exc)

    log_operational_error(
        LOGGER,
        i18n.t("splash_error_mensaje", incident_id=resolved_incident_id),
        exc=exc,
        extra={
            "incident_id": resolved_incident_id,
            "correlation_id": app._fallo_arranque_correlation_id,
        },
    )

    def _safe_quit_thread() -> None:
        safe_quit_thread(startup_thread)

    def _mostrar_dialogo_error() -> None:
        if getattr(app, "_fallo_arranque_dialogo_mostrado", False):
            return
        app._fallo_arranque_dialogo_mostrado = True

        if dialogo_factory is None:
            from app.ui.dialogos.dialogo_error_arranque import DialogoErrorArranque

            resolved_dialogo_factory = DialogoErrorArranque
        else:
            resolved_dialogo_factory = dialogo_factory

        dialogo = resolved_dialogo_factory(
            i18n,
            titulo=i18n.t("splash_error_titulo"),
            mensaje_usuario=mensaje_usuario or i18n.t("startup_error_dialog_message"),
            incident_id=resolved_incident_id,
            detalles=resolved_detalles,
            parent=None,
        )

        def _exit_con_codigo() -> None:
            QTimer.singleShot(0, lambda: QApplication.exit(2))

        safe_call(dialogo, "setWindowModality", Qt.ApplicationModal)
        safe_call(dialogo, "setWindowFlag", Qt.WindowStaysOnTopHint, True)
        if hasattr(dialogo, "finished"):
            dialogo.finished.connect(_exit_con_codigo)
        safe_call(dialogo, "show")
        safe_call(dialogo, "raise_")
        safe_call(dialogo, "activateWindow")
        if not hasattr(dialogo, "finished") and hasattr(dialogo, "exec"):
            safe_call(dialogo, "exec")
            _exit_con_codigo()

    def _do_fail_safe() -> None:
        if getattr(app, "_startup_fail_safe_ejecutado", False):
            return
        app._startup_fail_safe_ejecutado = True
        try:
            _stop_watchdog_en_main_thread(watchdog_timer)
            _safe_quit_thread()
            if _es_objeto_qt_valido(splash):
                _cerrar_splash_seguro(splash)
            if _es_objeto_qt_valido(splash) and hasattr(splash, "deleteLater"):
                try:
                    QTimer.singleShot(0, splash.deleteLater)
                except RuntimeError:
                    pass
        except Exception as cleanup_exc:  # noqa: BLE001
            log_operational_error(
                LOGGER,
                "STARTUP_FAILSAFE_CLEANUP_FAILED",
                exc=cleanup_exc,
                extra={"incident_id": resolved_incident_id},
            )
        try:
            _mostrar_dialogo_error()
        except Exception as dialog_exc:  # noqa: BLE001
            log_operational_error(
                LOGGER,
                "STARTUP_FAILSAFE_DIALOG_FAILED",
                exc=dialog_exc,
                extra={"incident_id": resolved_incident_id},
            )

    app_thread = (
        app.thread() if es_objeto_qt_valido(app) and hasattr(app, "thread") else None
    )
    if app_thread is not None and QThread.currentThread() is not app_thread:
        _enqueue_on_ui_thread(app, _do_fail_safe)
    else:
        _do_fail_safe()
    return resolved_incident_id


def _construir_dependencias_arranque(container):
    from infraestructura.proveedor_documentos import ProveedorDocumentosInfra
    from presentacion.orquestador_arranque import DependenciasArranque

    repo_pref = container.repositorio_preferencias
    proveedor_documentos = ProveedorDocumentosInfra()
    return DependenciasArranque(
        obtener_estado_onboarding=ObtenerEstadoOnboarding(repo_pref),
        marcar_onboarding_completado=MarcarOnboardingCompletado(repo_pref),
        guardar_preferencia_pantalla_completa=GuardarPreferenciaPantallaCompleta(
            repo_pref
        ),
        obtener_preferencia_pantalla_completa=ObtenerPreferenciaPantallaCompleta(
            repo_pref
        ),
        obtener_idioma_ui=ObtenerIdiomaUI(repo_pref),
        guardar_idioma_ui=GuardarIdiomaUI(repo_pref),
        obtener_ruta_guia_sync=ObtenerRutaGuiaSync(proveedor_documentos),
    )


def _actualizar_preferencias_en_hilo_ui(resolved_container, deps_arranque):
    """Reemplaza preferencias headless por QSettings desde el hilo de UI."""
    try:
        from infraestructura.repositorio_preferencias_qsettings import (
            RepositorioPreferenciasQSettings,
        )
    except Exception:
        return deps_arranque

    try:
        resolved_container.repositorio_preferencias = RepositorioPreferenciasQSettings()
    except Exception as exc:  # pragma: no cover - error dependiente de plataforma
        log_operational_error(
            LOGGER,
            "No se pudo crear RepositorioPreferenciasQSettings en hilo UI; se mantiene repositorio actual.",
            exc=exc,
        )
        return deps_arranque

    return _construir_dependencias_arranque(resolved_container)


def _instalar_menu_ayuda(
    main_window,
    i18n,
    reiniciar_onboarding: ReiniciarOnboarding,
    cargar_datos_demo: CargarDatosDemoCasoUso,
) -> None:
    from PySide6.QtWidgets import QMessageBox

    menu_ayuda = main_window.menuBar().addMenu(i18n.t("menu_ayuda"))
    accion_reiniciar = menu_ayuda.addAction(i18n.t("menu_reiniciar_asistente"))
    accion_cargar_demo = menu_ayuda.addAction(i18n.t("menu_cargar_demo"))

    def _reiniciar_asistente() -> None:
        respuesta = QMessageBox.question(
            main_window,
            i18n.t("menu_reiniciar_confirmar_titulo"),
            i18n.t("menu_reiniciar_confirmar_mensaje"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        reiniciar_onboarding.ejecutar()
        QMessageBox.information(
            main_window, i18n.t("menu_ayuda"), i18n.t("menu_reiniciar_ok")
        )

    def _cargar_demo() -> None:
        confirmacion = QMessageBox.question(
            main_window,
            i18n.t("menu_cargar_demo_confirmar_titulo"),
            i18n.t("menu_cargar_demo_confirmar_mensaje"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        resultado = cargar_datos_demo.ejecutar(modo="BACKUP")
        if resultado.ok:
            main_window._load_personas()
            main_window._reload_pending_views()
            main_window._refresh_historico(force=True)
            main_window._refresh_saldos()
            main_window.main_tabs.setCurrentIndex(0)
            main_window.toast.show(
                i18n.t("menu_cargar_demo_toast_ok"),
                level="success",
                title=i18n.t("menu_cargar_demo"),
                action_label=i18n.t("menu_cargar_demo_ir_solicitudes"),
                action_callback=lambda: main_window.main_tabs.setCurrentIndex(0),
            )
            return
        correlation_id = str(uuid.uuid4())
        main_window.toast.show(
            i18n.t("menu_cargar_demo_toast_error"),
            level="error",
            title=i18n.t("menu_cargar_demo"),
            action_label=i18n.t("menu_cargar_demo_ver_detalles"),
            action_callback=lambda: QMessageBox.critical(
                main_window,
                i18n.t("menu_cargar_demo"),
                resultado.detalles or i18n.t("menu_cargar_demo_error_sin_detalles"),
            ),
            details=resultado.detalles,
            correlation_id=correlation_id,
            code="DEMO_LOAD_FAILED",
        )

    accion_reiniciar.triggered.connect(_reiniciar_asistente)
    accion_cargar_demo.triggered.connect(_cargar_demo)


def run_ui(container=None) -> int:
    iniciar_captura_fallos_fatales(
        log_dir=project_root() / "logs",
        sobrescribir=True,
    )
    marcar_stage("UI_BOOT_INICIO")
    marcar_stage("UI_LOGGING_CONFIGURADO")

    from app.entrypoints.arranque_hilo import TrabajadorArranque
    from app.ui.estilos.apply_theme import aplicar_tema
    from app.ui.main_window import MainWindow
    from app.ui.splash_window import SplashWindow
    from app.ui.qt_hilos import assert_hilo_ui_o_log, ejecutar_en_hilo_ui
    from app.ui.theme import build_stylesheet
    from presentacion.i18n import I18nManager
    from presentacion.orquestador_arranque import OrquestadorArranqueUI

    from app.entrypoints.coordinador_arranque import CoordinadorArranque
    from PySide6.QtCore import QThread, QTimer, Qt
    from PySide6.QtWidgets import QApplication

    startup_timeout_ms = _resolver_startup_timeout_ms()

    app = QApplication([])
    marcar_stage("UI_QT_INICIALIZADO")
    quit_on_last_window_closed_previo = bool(app.quitOnLastWindowClosed())
    app.setProperty(
        "_quit_on_last_window_closed_previo", quit_on_last_window_closed_previo
    )
    app.aboutToQuit.connect(lambda: marcar_stage("about_to_quit"))
    app.lastWindowClosed.connect(lambda: marcar_stage("last_window_closed"))
    instalar_qt_message_handler(LOGGER, getattr(container, "boot_trace_writer", None))
    assert_hilo_ui_o_log("run_ui.bootstrap", LOGGER)
    i18n = I18nManager("es")
    splash = SplashWindow(i18n)
    splash.show()
    marcar_stage("splash_created")

    startup_thread = QThread(splash)
    startup_worker = TrabajadorArranque(container)
    startup_worker.moveToThread(startup_thread)
    splash.registrar_arranque(startup_thread, startup_worker)

    watchdog_timer = QTimer(splash)
    watchdog_timer.setSingleShot(True)
    watchdog_timer.setInterval(startup_timeout_ms)

    class CoordinadorArranquePrincipal(
        _CoordinadorArranqueConCierreDeterminista, CoordinadorArranque
    ):
        pass

    controlador = CoordinadorArranquePrincipal(
        app=app,
        i18n=i18n,
        splash=splash,
        startup_timeout_ms=startup_timeout_ms,
        startup_thread=startup_thread,
        startup_worker=startup_worker,
        watchdog_timer=watchdog_timer,
        main_window_factory=lambda resolved_container, deps_arranque: MainWindow(
            resolved_container.persona_use_cases,
            resolved_container.solicitud_use_cases,
            resolved_container.grupo_use_cases,
            resolved_container.sheets_service,
            resolved_container.sync_service,
            resolved_container.conflicts_service,
            resolved_container.health_check_use_case,
            resolved_container.alert_engine,
            resolved_container.validacion_preventiva_lock_use_case,
            resolved_container.confirmar_pendientes_pdf_caso_uso,
            resolved_container.crear_pendiente_caso_uso,
            guardar_preferencia_pantalla_completa=deps_arranque.guardar_preferencia_pantalla_completa,
            obtener_preferencia_pantalla_completa=deps_arranque.obtener_preferencia_pantalla_completa,
            servicio_i18n=resolved_container.servicio_i18n,
        ),
        orquestador_factory=OrquestadorArranqueUI,
        instalar_menu_ayuda=_instalar_menu_ayuda,
        fallo_arranque_handler=_manejar_fallo_arranque,
    )
    app._coordinador_arranque_ui = controlador
    app._startup_thread_ref = startup_thread
    app._startup_worker_ref = startup_worker
    controlador.desactivar_quit_on_last_window_closed_temporalmente()

    splash.registrar_watchdog(watchdog_timer)
    splash.registrar_cancelacion_arranque(
        controlador.solicitar_cancelacion_arranque_por_usuario
    )

    watchdog_timer.timeout.connect(
        controlador.on_timeout, Qt.ConnectionType.QueuedConnection
    )
    startup_worker.progreso.connect(
        controlador.on_progreso, Qt.ConnectionType.QueuedConnection
    )
    startup_worker.finished.connect(
        controlador.on_finished, Qt.ConnectionType.QueuedConnection
    )
    startup_worker.failed.connect(
        controlador.on_failed, Qt.ConnectionType.QueuedConnection
    )

    conexiones_arranque = (
        (watchdog_timer.timeout, controlador.on_timeout),
        (startup_worker.progreso, controlador.on_progreso),
        (startup_worker.finished, controlador.on_finished),
        (startup_worker.failed, controlador.on_failed),
    )

    def _limpiar_arranque() -> None:
        if getattr(controlador, "_arranque_limpio", False):
            return
        controlador._arranque_limpio = True
        for signal, slot in conexiones_arranque:
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                continue
        safe_call(startup_thread, "quit")
        if not getattr(startup_thread, "_delete_later_conectado", False):
            startup_thread.finished.connect(startup_thread.deleteLater)
            startup_thread._delete_later_conectado = True
        safe_call(startup_worker, "deleteLater")

    startup_worker.finished.connect(
        _limpiar_arranque, Qt.ConnectionType.QueuedConnection
    )
    startup_worker.failed.connect(_limpiar_arranque, Qt.ConnectionType.QueuedConnection)
    startup_thread.started.connect(startup_worker.run)

    try:
        try:
            aplicar_tema(app)
        except OSError:
            app.setStyleSheet(build_stylesheet())
        controlador.iniciar()
        ejecutar_en_hilo_ui(
            startup_thread.start,
            contexto="run_ui.startup_thread.start",
            logger=LOGGER,
        )
        marcar_stage("startup_thread_started")
        marcar_stage("run_ui_exec_enter")
        exit_code = app.exec()
        LOGGER.info("RUN_UI_EXEC_EXIT", extra={"extra": {"exit_code": exit_code}})
        marcar_stage("run_ui_exec_exit")
        return exit_code
    except Exception as exc:  # noqa: BLE001
        _manejar_fallo_arranque(
            exc=exc,
            trace_info=None,
            i18n=i18n,
            splash=splash,
            startup_thread=startup_thread,
            app=app,
            watchdog_timer=None,
        )
        return 2
