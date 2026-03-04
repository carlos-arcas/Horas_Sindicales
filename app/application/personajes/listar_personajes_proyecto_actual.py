from __future__ import annotations

from app.application.personajes.puertos import RepositorioPersonaje, RepositorioProyectoActual
from app.domain.personajes import Personaje


class ListarPersonajesProyectoActual:
    def __init__(self, repo_personaje: RepositorioPersonaje, repo_proyecto_actual: RepositorioProyectoActual) -> None:
        self._repo_personaje = repo_personaje
        self._repo_proyecto_actual = repo_proyecto_actual

    def ejecutar(self) -> list[Personaje]:
        proyecto_id = self._repo_proyecto_actual.obtener_proyecto_actual_id()
        if proyecto_id is None:
            return []
        return self._repo_personaje.listar_por_proyecto(proyecto_id)
