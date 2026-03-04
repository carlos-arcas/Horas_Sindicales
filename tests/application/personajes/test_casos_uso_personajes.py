from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.application.personajes import (
    CrearPersonajeProyectoActual,
    EditarPersonaje,
    EliminarPersonaje,
    ListarPersonajesProyectoActual,
)
from app.infrastructure.personajes import RepositorioPersonajeORM


@dataclass
class RepoProyectoActualFake:
    proyecto_id: UUID | None

    def obtener_proyecto_actual_id(self) -> UUID | None:
        return self.proyecto_id


def test_crear_y_listar_personajes_proyecto_actual() -> None:
    repo_personaje = RepositorioPersonajeORM()
    repo_proyecto = RepoProyectoActualFake(proyecto_id=uuid4())
    crear = CrearPersonajeProyectoActual(repo_personaje, repo_proyecto)
    listar = ListarPersonajesProyectoActual(repo_personaje, repo_proyecto)

    creado = crear.ejecutar("  Nami  ", "  navegante  ")

    assert creado is not None
    listado = listar.ejecutar()
    assert [item.nombre for item in listado] == ["Nami"]


def test_editar_y_eliminar_personaje() -> None:
    repo_personaje = RepositorioPersonajeORM()
    proyecto_id = uuid4()
    personaje = repo_personaje.crear(proyecto_id=proyecto_id, nombre="Luffy", descripcion="capitan")

    editar = EditarPersonaje(repo_personaje)
    eliminar = EliminarPersonaje(repo_personaje)

    actualizado = editar.ejecutar(personaje.id, "Luffy D.", "pirata")
    eliminar.ejecutar(actualizado.id)

    assert repo_personaje.obtener_por_id(actualizado.id) is None


def test_listar_personajes_sin_proyecto_actual_retorna_vacio() -> None:
    repo_personaje = RepositorioPersonajeORM()
    repo_proyecto = RepoProyectoActualFake(proyecto_id=None)

    listado = ListarPersonajesProyectoActual(repo_personaje, repo_proyecto).ejecutar()

    assert listado == []
