from __future__ import annotations

from typing import Protocol


class IProveedorI18N(Protocol):
    @property
    def idioma_actual(self) -> str:
        ...

    def idiomas_disponibles(self) -> tuple[str, ...]:
        ...

    def cambiar_idioma(self, idioma: str) -> str:
        ...

    def traducir(self, clave: str, **kwargs: object) -> str:
        ...
