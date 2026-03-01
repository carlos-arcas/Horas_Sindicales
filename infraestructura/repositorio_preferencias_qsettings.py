"""Repositorio de preferencias persistido en QSettings."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QSettings

from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias
from app.bootstrap.logging import log_operational_error

LOGGER = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


class RepositorioPreferenciasQSettings(IRepositorioPreferencias):
    """Implementación de preferencias booleanas sobre QSettings."""

    def __init__(
        self,
        settings: QSettings | None = None,
        *,
        organization: str = "HorasSindicales",
        application: str = "HorasSindicales",
    ) -> None:
        self._settings = settings or QSettings(organization, application)

    def obtener_bool(self, clave: str, por_defecto: bool) -> bool:
        if not self._settings.contains(clave):
            return por_defecto

        raw = self._settings.value(clave, por_defecto)
        coerced = _coerce_bool(raw)
        if coerced is None:
            log_operational_error(
                LOGGER,
                "Valor de preferencia inválido; se usa valor por defecto.",
                extra={"clave": clave, "valor": raw, "por_defecto": por_defecto},
            )
            return por_defecto
        return coerced

    def guardar_bool(self, clave: str, valor: bool) -> None:
        try:
            self._settings.setValue(clave, bool(valor))
            self._settings.sync()
        except Exception as exc:  # pragma: no cover - error de plataforma/IO
            log_operational_error(
                LOGGER,
                "Error guardando preferencia en QSettings.",
                exc=exc,
                extra={"clave": clave, "valor": bool(valor)},
            )
            raise


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return None

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
        return None

    return None
