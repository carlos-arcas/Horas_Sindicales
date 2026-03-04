from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.reportes_contenido import FiltroReportes, PeticionPaginada, ReporteContenido


@dataclass(frozen=True)
class EventoAuditoriaSeguridad:
    tipo_evento: str
    resultado: str
    reason_code: str
    actor_id: str
    recurso_tipo: str
    recurso_id: str
    fecha: datetime


class IAuditoriaSeguridadRepositorio(Protocol):
    def registrar(self, evento: EventoAuditoriaSeguridad) -> None:
        ...


class IReportesRepositorio(Protocol):
    def crear_si_no_existe_pendiente(self, reporte: ReporteContenido) -> bool:
        ...

    def listar_admin(self, filtro: FiltroReportes, paginacion: PeticionPaginada) -> tuple[list[ReporteContenido], int]:
        ...

    def obtener_por_id(self, reporte_id: str) -> ReporteContenido | None:
        ...

    def marcar_resuelto(self, reporte_id: str, admin_id: str, accion: str, comentario_admin: str | None) -> bool:
        ...


class IRecursosModeracionRepositorio(Protocol):
    def existe_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        ...

    def ocultar_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        ...
