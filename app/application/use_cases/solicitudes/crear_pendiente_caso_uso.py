from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Protocol

from app.application.dto import SolicitudDTO
from app.application.use_cases.politica_modo_solo_lectura import PoliticaModoSoloLectura
from app.core.observability import generate_correlation_id, log_event


logger = logging.getLogger(__name__)


class RepositorioSolicitudesCrearPendiente(Protocol):
    def crear_pendiente(self, solicitud: SolicitudDTO, correlation_id: str | None = None) -> SolicitudDTO: ...

    def listar_pendientes(self) -> list[SolicitudDTO]: ...


@dataclass(frozen=True)
class SolicitudCrearPendientePeticion:
    solicitud: SolicitudDTO
    correlation_id: str | None = None


@dataclass(frozen=True)
class SolicitudCrearPendienteResultado:
    solicitud_id: int | None
    solicitud_creada: SolicitudDTO | None
    pendientes_ids: list[int] = field(default_factory=list)
    requiere_refresh: bool = True
    errores: list[str] = field(default_factory=list)


@dataclass
class CrearPendienteCasoUso:
    repositorio: RepositorioSolicitudesCrearPendiente
    politica_modo_solo_lectura: PoliticaModoSoloLectura

    def execute(self, request: SolicitudCrearPendientePeticion) -> SolicitudCrearPendienteResultado:
        correlation_id = request.correlation_id or generate_correlation_id()
        log_event(
            logger,
            "crear_pendiente_started",
            {
                "persona_id": request.solicitud.persona_id,
                "fecha_pedida": request.solicitud.fecha_pedida,
            },
            correlation_id,
        )
        self.politica_modo_solo_lectura.verificar()
        try:
            creada = self.repositorio.crear_pendiente(request.solicitud, correlation_id=correlation_id)
            pendientes = self.repositorio.listar_pendientes()
        except Exception as exc:
            log_event(logger, "crear_pendiente_finished", {"ok": False, "errores": 1}, correlation_id)
            return SolicitudCrearPendienteResultado(
                solicitud_id=None,
                solicitud_creada=None,
                errores=[str(exc)],
            )

        pendientes_ids = [item.id for item in pendientes if item.id is not None]
        log_event(
            logger,
            "crear_pendiente_finished",
            {
                "ok": True,
                "solicitud_id": creada.id,
                "pendientes_count": len(pendientes_ids),
            },
            correlation_id,
        )
        return SolicitudCrearPendienteResultado(
            solicitud_id=creada.id,
            solicitud_creada=creada,
            pendientes_ids=pendientes_ids,
        )
