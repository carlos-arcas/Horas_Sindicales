from __future__ import annotations

from dataclasses import dataclass

from app.application.personajes import (
    CrearPersonajeProyectoActual,
    EditarPersonaje,
    EliminarPersonaje,
    ListarPersonajesProyectoActual,
    RepositorioProyectoActual,
)
from app.infrastructure.personajes import RepositorioPersonajeORM


@dataclass(frozen=True)
class PersonajesFacade:
    listar_personajes_proyecto_actual: ListarPersonajesProyectoActual
    crear_personaje_proyecto_actual: CrearPersonajeProyectoActual
    editar_personaje: EditarPersonaje
    eliminar_personaje: EliminarPersonaje


def build_personajes_facade(repo_proyecto_actual: RepositorioProyectoActual) -> PersonajesFacade:
    repo_personaje = RepositorioPersonajeORM()
    return PersonajesFacade(
        listar_personajes_proyecto_actual=ListarPersonajesProyectoActual(repo_personaje, repo_proyecto_actual),
        crear_personaje_proyecto_actual=CrearPersonajeProyectoActual(repo_personaje, repo_proyecto_actual),
        editar_personaje=EditarPersonaje(repo_personaje),
        eliminar_personaje=EliminarPersonaje(repo_personaje),
    )
