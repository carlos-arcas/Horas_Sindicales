"""Paquete puente (compatibilidad). Fuente real: app/infrastructure."""

from app.infrastructure import *  # noqa: F401,F403
from infraestructura.repositorio_preferencias_qsettings import (
    RepositorioPreferenciasQSettings as RepositorioPreferenciasQSettings,
)

__all__ = ["RepositorioPreferenciasQSettings"]
