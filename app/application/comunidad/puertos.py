from __future__ import annotations

from typing import Protocol

from app.domain.comunidad_descubrimiento import FiltroDescubrimiento, PerfilSugerido, PublicacionDescubrimiento


class RepositorioComunidadPuerto(Protocol):
    def listar_publicaciones(self, filtro: FiltroDescubrimiento) -> list[PublicacionDescubrimiento]: ...

    def listar_disciplinas_disponibles(self) -> list[str]: ...

    def listar_perfiles_sugeridos(self, limite: int = 5) -> list[PerfilSugerido]: ...
