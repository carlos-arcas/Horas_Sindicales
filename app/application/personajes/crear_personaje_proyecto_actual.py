from __future__ import annotations

from app.application.personajes.puertos import RepositorioPersonaje, RepositorioProyectoActual
from app.domain.personajes import Personaje, normalizar_nombre_personaje, validar_descripcion_personaje


class CrearPersonajeProyectoActual:
    def __init__(self, repo_personaje: RepositorioPersonaje, repo_proyecto_actual: RepositorioProyectoActual) -> None:
        self._repo_personaje = repo_personaje
        self._repo_proyecto_actual = repo_proyecto_actual

    def ejecutar(self, nombre: str, descripcion: str) -> Personaje | None:
        proyecto_id = self._repo_proyecto_actual.obtener_proyecto_actual_id()
        if proyecto_id is None:
            return None
        return self._repo_personaje.crear(
            proyecto_id=proyecto_id,
            nombre=normalizar_nombre_personaje(nombre),
            descripcion=validar_descripcion_personaje(descripcion),
        )
