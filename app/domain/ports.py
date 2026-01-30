from __future__ import annotations

from typing import Protocol, Iterable

from app.domain.models import Persona, Solicitud


class PersonaRepository(Protocol):
    def list_all(self) -> Iterable[Persona]:
        ...

    def get_by_nombre(self, nombre: str) -> Persona | None:
        ...

    def create(self, persona: Persona) -> Persona:
        ...


class SolicitudRepository(Protocol):
    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        ...

    def create(self, solicitud: Solicitud) -> Solicitud:
        ...
