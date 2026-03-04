from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.personajes import Personaje


class RepositorioPersonaje(Protocol):
    def crear(self, proyecto_id: UUID, nombre: str, descripcion: str) -> Personaje: ...

    def listar_por_proyecto(self, proyecto_id: UUID) -> list[Personaje]: ...

    def obtener_por_id(self, personaje_id: UUID) -> Personaje | None: ...

    def editar(self, personaje_id: UUID, nombre: str, descripcion: str) -> Personaje: ...

    def eliminar(self, personaje_id: UUID) -> None: ...


class RepositorioProyectoActual(Protocol):
    def obtener_proyecto_actual_id(self) -> UUID | None: ...
