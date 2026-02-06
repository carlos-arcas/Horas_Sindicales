from __future__ import annotations

from pathlib import Path
from typing import Protocol, Iterable

from app.domain.models import GrupoConfig, Persona, SheetsConfig, Solicitud


class PersonaRepository(Protocol):
    def list_all(self, include_inactive: bool = False) -> Iterable[Persona]:
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

    def list_by_persona_and_fecha(self, persona_id: int, fecha_pedida: str) -> Iterable[Solicitud]:
        ...

    def get_by_id(self, solicitud_id: int) -> Solicitud | None:
        ...

    def exists_duplicate(
        self,
        persona_id: int,
        fecha_pedida: str,
        desde_min: int | None,
        hasta_min: int | None,
        completo: bool,
    ) -> bool:
        ...

    def create(self, solicitud: Solicitud) -> Solicitud:
        ...

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        ...

    def delete(self, solicitud_id: int) -> None:
        ...

    def delete_by_ids(self, solicitud_ids: Iterable[int]) -> None:
        ...


class GrupoConfigRepository(Protocol):
    def get(self) -> GrupoConfig | None:
        ...

    def upsert(self, config: GrupoConfig) -> GrupoConfig:
        ...


class SheetsConfigRepository(Protocol):
    def load(self) -> SheetsConfig | None:
        ...

    def save(self, config: SheetsConfig) -> SheetsConfig:
        ...

    def credentials_path(self) -> Path:
        ...
