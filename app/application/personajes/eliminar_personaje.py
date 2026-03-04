from __future__ import annotations

from uuid import UUID

from app.application.personajes.puertos import RepositorioPersonaje


class EliminarPersonaje:
    def __init__(self, repo_personaje: RepositorioPersonaje) -> None:
        self._repo_personaje = repo_personaje

    def ejecutar(self, personaje_id: UUID) -> None:
        self._repo_personaje.eliminar(personaje_id)
