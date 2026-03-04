from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.application.reportes.puertos import (
    EventoAuditoriaSeguridad,
    IAuditoriaSeguridadRepositorio,
    IRecursosModeracionRepositorio,
    IReportesRepositorio,
)
from app.domain.reportes_contenido import (
    FiltroReportes,
    PeticionPaginada,
    ReporteContenido,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorFuncionalReporte(Exception):
    reason_code: str


@dataclass(frozen=True)
class ResultadoCrearReporte:
    accion: str
    reporte_id: str | None
    mensaje: str


@dataclass(frozen=True)
class ResultadoResolverReporte:
    accion: str
    mensaje: str


class CrearReporteContenido:
    def __init__(self, reportes_repo: IReportesRepositorio, recursos_repo: IRecursosModeracionRepositorio) -> None:
        self._reportes_repo = reportes_repo
        self._recursos_repo = recursos_repo

    def ejecutar(self, *, denunciante_id: str, recurso_tipo: str, recurso_id: str, motivo: str, detalle: str | None) -> ResultadoCrearReporte:
        if not self._recursos_repo.existe_recurso(recurso_tipo, recurso_id):
            logger.warning("reportes.crear", extra={"resultado": "fail", "reason_code": "recurso_no_encontrado"})
            raise ErrorFuncionalReporte("recurso_no_encontrado")
        reporte = ReporteContenido(
            reporte_id=str(uuid.uuid4()),
            denunciante_id=denunciante_id,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            motivo=motivo,
            detalle=detalle,
            estado="pendiente",
            creado_en=datetime.now(timezone.utc),
        )
        creado = self._reportes_repo.crear_si_no_existe_pendiente(reporte)
        if not creado:
            logger.info("reportes.crear", extra={"resultado": "ok", "accion": "ya_existia"})
            return ResultadoCrearReporte(accion="ya_existia", reporte_id=None, mensaje="reportes_ya_existia")
        logger.info("reportes.crear", extra={"resultado": "ok", "accion": "creado"})
        return ResultadoCrearReporte(accion="creado", reporte_id=reporte.reporte_id, mensaje="reportes_creado")


class ListarReportesAdmin:
    def __init__(self, reportes_repo: IReportesRepositorio) -> None:
        self._reportes_repo = reportes_repo

    def ejecutar(self, *, admin_id: str, filtro: FiltroReportes, paginacion: PeticionPaginada) -> dict[str, object]:
        items, total = self._reportes_repo.listar_admin(filtro, paginacion)
        logger.info("admin.reportes.listar", extra={"resultado": "ok", "admin_id": admin_id, "total": total})
        return {"items": items, "limit": paginacion.limit, "offset": paginacion.offset, "total": total}


class ResolverReporteAdmin:
    def __init__(
        self,
        reportes_repo: IReportesRepositorio,
        recursos_repo: IRecursosModeracionRepositorio,
        auditoria_repo: IAuditoriaSeguridadRepositorio,
    ) -> None:
        self._reportes_repo = reportes_repo
        self._recursos_repo = recursos_repo
        self._auditoria_repo = auditoria_repo

    def ejecutar(self, *, admin_id: str, reporte_id: str, accion: str, comentario_admin: str | None) -> ResultadoResolverReporte:
        reporte = self._reportes_repo.obtener_por_id(reporte_id)
        if reporte is None:
            logger.warning("admin.reportes.resolver", extra={"resultado": "fail", "reason_code": "reporte_no_encontrado"})
            raise ErrorFuncionalReporte("reporte_no_encontrado")
        if reporte.estado != "pendiente":
            logger.info("admin.reportes.resolver", extra={"resultado": "ok", "accion": "ya_resuelto"})
            return ResultadoResolverReporte(accion="ya_resuelto", mensaje="reportes_admin_ya_resuelto")

        accion_final = accion
        if accion == "ocultar_recurso" and not self._recursos_repo.ocultar_recurso(reporte.recurso_tipo, reporte.recurso_id):
            accion_final = "descartar"

        self._reportes_repo.marcar_resuelto(reporte_id, admin_id, accion_final, comentario_admin)
        self._auditoria_repo.registrar(
            EventoAuditoriaSeguridad(
                tipo_evento="admin_reporte_resuelto",
                resultado="ok",
                reason_code=accion_final,
                actor_id=admin_id,
                recurso_tipo=reporte.recurso_tipo,
                recurso_id=reporte.recurso_id,
                fecha=datetime.now(timezone.utc),
            )
        )
        logger.info("admin.reportes.resolver", extra={"resultado": "ok", "accion": accion_final})
        return ResultadoResolverReporte(accion="resuelto", mensaje="reportes_admin_resuelto")
