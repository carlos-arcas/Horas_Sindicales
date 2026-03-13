from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class NombreCapacidadOpcional(StrEnum):
    MODAL_SALDOS_DETALLE = "modal_saldos_detalle"


CAPACIDAD_MODAL_SALDOS_DETALLE = NombreCapacidadOpcional.MODAL_SALDOS_DETALLE


@dataclass(slots=True)
class RegistroCapacidadesOpcionales:
    """Registro encapsulado para capacidades opcionales de UI."""

    _capacidades: dict[NombreCapacidadOpcional, Any] = field(default_factory=dict)

    @classmethod
    def desde_mapa(cls, capacidades: Mapping[str | NombreCapacidadOpcional, Any] | None) -> RegistroCapacidadesOpcionales:
        registro = cls()
        if capacidades is None:
            return registro
        for nombre_capacidad, implementacion in capacidades.items():
            registro.registrar(nombre_capacidad, implementacion)
        return registro

    def registrar(self, nombre_capacidad: str | NombreCapacidadOpcional, implementacion: Any) -> None:
        nombre_normalizado = _normalizar_nombre_capacidad(nombre_capacidad)
        self._capacidades[nombre_normalizado] = implementacion

    def obtener(self, nombre_capacidad: str | NombreCapacidadOpcional) -> Any | None:
        nombre_normalizado = _normalizar_nombre_capacidad(nombre_capacidad)
        return self._capacidades.get(nombre_normalizado)

    def disponible(self, nombre_capacidad: str | NombreCapacidadOpcional) -> bool:
        return self.obtener(nombre_capacidad) is not None


def registrar_capacidades_opcionales(
    window: object,
    capacidades: Mapping[str | NombreCapacidadOpcional, Any] | None,
) -> None:
    """Registra capacidades opcionales de forma explícita en la ventana."""

    window.registro_capacidades_opcionales = RegistroCapacidadesOpcionales.desde_mapa(capacidades)


def obtener_capacidad_opcional(window: object, nombre_capacidad: str | NombreCapacidadOpcional) -> Any | None:
    """Obtiene una capacidad opcional declarada en la ventana."""

    registro = _obtener_registro(window)
    if registro is None:
        return None
    return registro.obtener(nombre_capacidad)


def capacidad_disponible(window: object, nombre_capacidad: str | NombreCapacidadOpcional) -> bool:
    """Indica si una capacidad opcional está disponible y es usable."""

    registro = _obtener_registro(window)
    if registro is None:
        return False
    return registro.disponible(nombre_capacidad)


def _obtener_registro(window: object) -> RegistroCapacidadesOpcionales | None:
    registro = getattr(window, "registro_capacidades_opcionales", None)
    if isinstance(registro, RegistroCapacidadesOpcionales):
        return registro
    return None


def _normalizar_nombre_capacidad(nombre_capacidad: str | NombreCapacidadOpcional) -> NombreCapacidadOpcional:
    if isinstance(nombre_capacidad, NombreCapacidadOpcional):
        return nombre_capacidad
    return NombreCapacidadOpcional(nombre_capacidad)
