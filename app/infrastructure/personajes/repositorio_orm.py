from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.personajes import Personaje


class RepositorioPersonajeORM:
    """Adaptador simple para pruebas; permite inyectar persistencia real desde Django."""

    def __init__(self) -> None:
        self._items: dict[UUID, Personaje] = {}

    def crear(self, proyecto_id: UUID, nombre: str, descripcion: str) -> Personaje:
        ahora = datetime.now(UTC)
        personaje = Personaje(
            id=uuid4(),
            proyecto_id=proyecto_id,
            nombre=nombre,
            descripcion=descripcion,
            creado_en=ahora,
            actualizado_en=ahora,
        )
        self._items[personaje.id] = personaje
        return personaje

    def listar_por_proyecto(self, proyecto_id: UUID) -> list[Personaje]:
        return [item for item in self._items.values() if item.proyecto_id == proyecto_id]

    def obtener_por_id(self, personaje_id: UUID) -> Personaje | None:
        return self._items.get(personaje_id)

    def editar(self, personaje_id: UUID, nombre: str, descripcion: str) -> Personaje:
        personaje = self._items[personaje_id]
        actualizado = Personaje(
            id=personaje.id,
            proyecto_id=personaje.proyecto_id,
            nombre=nombre,
            descripcion=descripcion,
            creado_en=personaje.creado_en,
            actualizado_en=datetime.now(UTC),
        )
        self._items[personaje_id] = actualizado
        return actualizado

    def eliminar(self, personaje_id: UUID) -> None:
        self._items.pop(personaje_id, None)
