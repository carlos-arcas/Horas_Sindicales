from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

ORDENES_DESCUBRIMIENTO = ("recientes", "populares", "siguiendo")


class ErrorDescubrimiento(ValueError):
    """Error base para validaciones de descubrimiento."""


class ErrorOrdenInvalido(ErrorDescubrimiento):
    pass


class ErrorLimiteInvalido(ErrorDescubrimiento):
    pass


@dataclass(frozen=True)
class FiltroDescubrimiento:
    orden: str = "recientes"
    disciplina: str | None = None
    busqueda: str | None = None
    limit: int = 20

    def __post_init__(self) -> None:
        if self.orden not in ORDENES_DESCUBRIMIENTO:
            raise ErrorOrdenInvalido(self.orden)
        if self.limit < 1 or self.limit > 50:
            raise ErrorLimiteInvalido("limit_fuera_de_rango")
        disciplina = self.disciplina.strip() if self.disciplina else None
        busqueda = self.busqueda.strip() if self.busqueda else None
        object.__setattr__(self, "disciplina", disciplina)
        object.__setattr__(self, "busqueda", busqueda)


@dataclass(frozen=True)
class PerfilSugerido:
    perfil_id: str
    alias: str
    disciplina_principal: str
    seguidores: int


@dataclass(frozen=True)
class PublicacionDescubrimiento:
    publicacion_id: str
    perfil_id: str
    alias_perfil: str
    disciplina: str
    titulo: str
    resumen: str
    likes: int
    comentarios: int
    publicado_en: datetime


@dataclass(frozen=True)
class ResultadoDescubrimiento:
    publicaciones: tuple[PublicacionDescubrimiento, ...]
    disciplinas: tuple[str, ...]
    perfiles_sugeridos: tuple[PerfilSugerido, ...]
    pestaña_siguiendo_habilitada: bool
