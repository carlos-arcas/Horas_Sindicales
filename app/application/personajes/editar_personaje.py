from __future__ import annotations

from uuid import UUID

from app.application.personajes.puertos import RepositorioPersonaje
from app.domain.personajes import Personaje, normalizar_nombre_personaje, validar_descripcion_personaje


class EditarPersonaje:
    def __init__(self, repo_personaje: RepositorioPersonaje) -> None:
        self._repo_personaje = repo_personaje

    def ejecutar(self, personaje_id: UUID, nombre: str, descripcion: str) -> Personaje:
        return self._repo_personaje.editar(
            personaje_id,
            normalizar_nombre_personaje(nombre),
            validar_descripcion_personaje(descripcion),
        )
