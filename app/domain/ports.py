from __future__ import annotations

from typing import Protocol, Iterable

from app.domain.models import Persona, Solicitud


class PersonaRepository(Protocol):
    def list_all(self) -> Iterable[Persona]:
        ...

    def get_by_id(self, persona_id: int) -> Persona | None:
        ...

    def get_by_nombre(self, nombre: str) -> Persona | None:
        ...

    def create(self, persona: Persona) -> Persona:
        ...

    def update(self, persona: Persona) -> Persona:
        ...


class SolicitudRepository(Protocol):
    def list_by_persona(self, persona_id: int) -> Iterable[Solicitud]:
        ...

    def list_by_persona_and_period(
        self, persona_id: int, year: int, month: int | None = None
    ) -> Iterable[Solicitud]:
        ...

    def get_by_id(self, solicitud_id: int) -> Solicitud | None:
        ...

    def exists_duplicate(
        self,
        persona_id: int,
        fecha_pedida: str,
        desde: str | None,
        hasta: str | None,
        completo: bool,
    ) -> bool:
        ...

    def create(self, solicitud: Solicitud) -> Solicitud:
        ...

    def delete(self, solicitud_id: int) -> None:
        ...
