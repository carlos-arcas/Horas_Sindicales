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
        "wizard_bienvenida_texto": "Te guiaremos por los puntos esenciales para empezar.",
        "wizard_conceptos_texto": "Gestiona solicitudes locales y sincroniza cuando lo necesites.",
        "wizard_sync_texto": "Sync envía cambios pendientes y evita duplicados con reglas de idempotencia.",
        "wizard_boton_ver_guia_sync": "Ver guía del Sync",
        "wizard_pref_fullscreen": "Abrir en pantalla completa por defecto",
        "wizard_pref_idioma": "Idioma",
        "wizard_boton_atras": "Atrás",
        "wizard_boton_siguiente": "Siguiente",
        "wizard_boton_finalizar": "Finalizar",
        "wizard_progreso": "Paso {actual} de {total}",
        "wizard_sync_dialog_titulo": "Guía de Sync",
        "wizard_sync_dialog_error": "No se pudo cargar la guía de Sync.",
        "menu_ayuda": "Ayuda",
        "menu_reiniciar_asistente": "Reiniciar asistente",
        "menu_reiniciar_ok": "El asistente se mostrará de nuevo en el próximo inicio.",
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
        "wizard_bienvenida_texto": "We will guide you through the essentials to get started.",
        "wizard_conceptos_texto": "Manage local requests and sync when needed.",
        "wizard_sync_texto": "Sync sends pending changes and avoids duplicates with idempotency rules.",
        "wizard_boton_ver_guia_sync": "Open Sync guide",
        "wizard_pref_fullscreen": "Open in full screen by default",
        "wizard_pref_idioma": "Language",
        "wizard_boton_atras": "Back",
        "wizard_boton_siguiente": "Next",
        "wizard_boton_finalizar": "Finish",
        "wizard_progreso": "Step {actual} of {total}",
        "wizard_sync_dialog_titulo": "Sync guide",
        "wizard_sync_dialog_error": "Unable to load Sync guide.",
        "menu_ayuda": "Help",
        "menu_reiniciar_asistente": "Restart wizard",
        "menu_reiniciar_ok": "The wizard will be shown again on next startup.",
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
