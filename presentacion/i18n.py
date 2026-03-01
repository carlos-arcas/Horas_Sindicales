from __future__ import annotations

from PySide6.QtCore import QObject, Signal


CATALOGO: dict[str, dict[str, str]] = {
    "es": {
        "splash_titulo": "Iniciando Horas Sindicales…",
        "splash_subtitulo": "Preparando configuración y servicios",
        "splash_cargando": "Cargando…",
        "splash_error_titulo": "Error inesperado",
        "splash_error_mensaje": "No se pudo completar el arranque. ID de incidente: {incident_id}",
        "wizard_titulo": "Asistente de bienvenida",
        "wizard_paso_1": "Bienvenida",
        "wizard_paso_2": "Conceptos básicos",
        "wizard_paso_3": "Sync",
        "wizard_paso_4": "Preferencias",
        "wizard_bienvenida_texto": "Esta app te ayuda a registrar y gestionar horas sindicales de forma clara.",
        "wizard_conceptos_texto": "Crédito es tu saldo disponible. Registro es cada solicitud que guardas en la app.",
        "wizard_sync_texto": "Sync es necesario para mantener coordinado el grupo de delegadas y compartir credenciales de acceso.",
        "wizard_boton_ver_guia_sync": "Ver guía paso a paso",
        "wizard_pref_fullscreen": "Abrir en pantalla completa por defecto",
        "wizard_pref_idioma": "Idioma",
        "wizard_idioma_es": "Español",
        "wizard_idioma_en": "Inglés",
        "wizard_boton_atras": "Atrás",
        "wizard_boton_siguiente": "Siguiente",
        "wizard_boton_finalizar": "Finalizar",
        "wizard_progreso": "Paso {actual} de {total}",
        "wizard_sync_dialog_titulo": "Guía de Sync",
        "wizard_sync_dialog_error": "No se pudo cargar la guía de Sync.",
        "menu_ayuda": "Ayuda",
        "menu_reiniciar_asistente": "Reiniciar asistente",
        "menu_reiniciar_ok": "El asistente se mostrará de nuevo en el próximo inicio.",
        "menu_reiniciar_confirmar_titulo": "Confirmar reinicio del asistente",
        "menu_reiniciar_confirmar_mensaje": "¿Quieres reiniciar el asistente de bienvenida?",
        "menu_cargar_demo": "Cargar datos de demostración",
        "menu_cargar_demo_confirmar_titulo": "Confirmar carga de datos demo",
        "menu_cargar_demo_confirmar_mensaje": "Se creará un backup automático y se reemplazarán los datos actuales por un dataset de demostración. ¿Deseas continuar?",
        "menu_cargar_demo_toast_ok": "Demo cargada",
        "menu_cargar_demo_toast_error": "No se pudo cargar la demo",
        "menu_cargar_demo_ir_solicitudes": "Ir a Solicitudes",
        "menu_cargar_demo_ver_detalles": "Ver detalles",
        "menu_cargar_demo_error_sin_detalles": "No hay detalles adicionales.",
        "dialogo_accion_confirmar": "Confirmar",
        "dialogo_accion_cancelar": "Cancelar",
        "startup_error_dialog_message": "No se pudo completar el arranque de la aplicación.",
        "startup_error_incident_label": "ID de incidente: {incident_id}",
        "startup_error_copy_id": "Copiar ID",
        "startup_error_open_logs": "Abrir carpeta de logs",
        "bootstrap.container": "Preparando contenedor…",
        "bootstrap.deps_arranque": "Preparando dependencias de arranque…",
        "bootstrap.crear_mainwindow_deps": "Preparando datos de ventana principal…",
        "startup_timeout_message": "Arranque tardando más de lo normal",
        "startup_last_stage": "Última etapa: {etapa}",
        "startup_worker_no_terminal_signal": "El worker de arranque no emitió señal terminal. Etapa: {etapa}",
        "sync_permission_blocked_message_with_email": "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con {service_account_email} como Editor.",
        "sync_permission_blocked_message_without_email": "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con la cuenta de servicio como Editor.",
    },
    "en": {
        "splash_titulo": "Starting Horas Sindicales…",
        "splash_subtitulo": "Preparing configuration and services",
        "splash_cargando": "Loading…",
        "splash_error_titulo": "Unexpected error",
        "splash_error_mensaje": "Startup could not be completed. Incident ID: {incident_id}",
        "wizard_titulo": "Welcome wizard",
        "wizard_paso_1": "Welcome",
        "wizard_paso_2": "Basics",
        "wizard_paso_3": "Sync",
        "wizard_paso_4": "Preferences",
        "wizard_bienvenida_texto": "This app helps you register and manage union hours in a simple way.",
        "wizard_conceptos_texto": "Credit is your available balance. A record is each request you save in the app.",
        "wizard_sync_texto": "Sync is needed to keep the delegates group coordinated and to share access credentials.",
        "wizard_boton_ver_guia_sync": "Open step-by-step guide",
        "wizard_pref_fullscreen": "Open in full screen by default",
        "wizard_pref_idioma": "Language",
        "wizard_idioma_es": "Spanish",
        "wizard_idioma_en": "English",
        "wizard_boton_atras": "Back",
        "wizard_boton_siguiente": "Next",
        "wizard_boton_finalizar": "Finish",
        "wizard_progreso": "Step {actual} of {total}",
        "wizard_sync_dialog_titulo": "Sync guide",
        "wizard_sync_dialog_error": "Unable to load Sync guide.",
        "menu_ayuda": "Help",
        "menu_reiniciar_asistente": "Restart wizard",
        "menu_reiniciar_ok": "The wizard will be shown again on next startup.",
        "menu_reiniciar_confirmar_titulo": "Confirm wizard restart",
        "menu_reiniciar_confirmar_mensaje": "Do you want to restart the welcome wizard?",
        "menu_cargar_demo": "Load demo data",
        "menu_cargar_demo_confirmar_titulo": "Confirm demo data load",
        "menu_cargar_demo_confirmar_mensaje": "An automatic backup will be created and current data will be replaced by a demo dataset. Continue?",
        "menu_cargar_demo_toast_ok": "Demo loaded",
        "menu_cargar_demo_toast_error": "Demo could not be loaded",
        "menu_cargar_demo_ir_solicitudes": "Go to Requests",
        "menu_cargar_demo_ver_detalles": "View details",
        "menu_cargar_demo_error_sin_detalles": "No additional details.",
        "dialogo_accion_confirmar": "Confirm",
        "dialogo_accion_cancelar": "Cancel",
        "startup_error_dialog_message": "The application startup could not be completed.",
        "startup_error_incident_label": "Incident ID: {incident_id}",
        "startup_error_copy_id": "Copy ID",
        "startup_error_open_logs": "Open logs folder",
        "bootstrap.container": "Preparing container…",
        "bootstrap.deps_arranque": "Preparing startup dependencies…",
        "bootstrap.crear_mainwindow_deps": "Preparing main window data…",
        "startup_timeout_message": "Startup is taking longer than expected",
        "startup_last_stage": "Last stage: {etapa}",
        "startup_worker_no_terminal_signal": "Startup worker did not emit a terminal signal. Stage: {etapa}",
        "sync_permission_blocked_message_with_email": "Sync is blocked due to permissions.\nShare the spreadsheet with {service_account_email} as Editor.",
        "sync_permission_blocked_message_without_email": "Sync is blocked due to permissions.\nShare the spreadsheet with the service account as Editor.",
    },
}


class I18nManager(QObject):
    idioma_cambiado = Signal(str)

    def __init__(self, idioma: str = "es") -> None:
        super().__init__()
        self._idioma = idioma if idioma in CATALOGO else "es"

    @property
    def idioma(self) -> str:
        return self._idioma

    def set_idioma(self, idioma: str) -> None:
        nuevo = idioma if idioma in CATALOGO else "es"
        if nuevo == self._idioma:
            return
        self._idioma = nuevo
        self.idioma_cambiado.emit(nuevo)

    def t(self, key: str, **kwargs: object) -> str:
        base = CATALOGO.get(self._idioma, CATALOGO["es"]).get(key, key)
        return base.format(**kwargs) if kwargs else base
