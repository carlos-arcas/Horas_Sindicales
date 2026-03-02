"""API pública de :mod:`presentacion` sin cargas implícitas de GUI."""

from presentacion.i18n import CATALOGO as CATALOGO, GestorI18N as GestorI18N, I18nManager as I18nManager, crear_gestor_i18n as crear_gestor_i18n
from presentacion.orquestador_arranque import DependenciasArranque as DependenciasArranque, OrquestadorArranqueUI as OrquestadorArranqueUI
