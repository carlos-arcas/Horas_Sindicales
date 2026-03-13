from __future__ import annotations

from typing import Any


CAPACIDAD_MODAL_SALDOS_DETALLE = "modal_saldos_detalle"


def registrar_capacidades_opcionales(window: object, capacidades: dict[str, Any] | None) -> None:
    """Registra capacidades opcionales de forma explícita en la ventana."""

    capacidades_normalizadas = dict(capacidades or {})
    window.capacidades_opcionales = capacidades_normalizadas


def obtener_capacidad_opcional(window: object, nombre_capacidad: str) -> Any | None:
    """Obtiene una capacidad opcional declarada en la ventana."""

    capacidades = getattr(window, "capacidades_opcionales", None)
    if not isinstance(capacidades, dict):
        return None
    return capacidades.get(nombre_capacidad)


def capacidad_disponible(window: object, nombre_capacidad: str) -> bool:
    """Indica si una capacidad opcional está disponible y es usable."""

    return obtener_capacidad_opcional(window, nombre_capacidad) is not None

