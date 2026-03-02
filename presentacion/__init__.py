"""API pública de :mod:`presentacion`.

Este paquete no importa automáticamente módulos de interfaz gráfica (por ejemplo,
``app.ui``) para evitar cargas implícitas de PySide6/libEGL en entornos sin GUI.

Si se necesitan clases o componentes visuales, deben importarse de forma
explícita desde sus módulos concretos.
"""

from presentacion.i18n import CATALOGO, GestorI18N, I18nManager, crear_gestor_i18n
from presentacion.orquestador_arranque import DependenciasArranque, OrquestadorArranqueUI

__all__ = [
    "CATALOGO",
    "GestorI18N",
    "I18nManager",
    "crear_gestor_i18n",
    "DependenciasArranque",
    "OrquestadorArranqueUI",
]
