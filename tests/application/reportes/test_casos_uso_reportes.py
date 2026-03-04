from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.application.reportes.casos_uso import (
    CrearReporteContenido,
    ErrorFuncionalReporte,
    ResolverReporteAdmin,
)
from app.application.reportes.puertos import EventoAuditoriaSeguridad
from app.domain.reportes_contenido import ReporteContenido


class RepoReportesFake:
    def __init__(self) -> None:
        self.por_id: dict[str, ReporteContenido] = {}
        self.creado = False

    def crear_si_no_existe_pendiente(self, reporte: ReporteContenido) -> bool:
        self.ultimo_creado = reporte
        if self.creado:
            return False
        self.creado = True
        self.por_id[reporte.reporte_id] = reporte
        return True

    def listar_admin(self, filtro, paginacion):
        return list(self.por_id.values()), len(self.por_id)

    def obtener_por_id(self, reporte_id: str) -> ReporteContenido | None:
        return self.por_id.get(reporte_id)

    def marcar_resuelto(self, reporte_id: str, admin_id: str, accion: str, comentario_admin: str | None) -> bool:
        reporte = self.por_id.get(reporte_id)
        if reporte is None or reporte.estado != "pendiente":
            return False
        estado = "descartado" if accion == "descartar" else "resuelto"
        self.por_id[reporte_id] = ReporteContenido(
            reporte_id=reporte.reporte_id,
            denunciante_id=reporte.denunciante_id,
            recurso_tipo=reporte.recurso_tipo,
            recurso_id=reporte.recurso_id,
            motivo=reporte.motivo,
            detalle=reporte.detalle,
            estado=estado,
            creado_en=reporte.creado_en,
        )
        return True


class RepoRecursosFake:
    def __init__(self, *, existe: bool = True, oculta: bool = True) -> None:
        self.existe = existe
        self.oculta = oculta
        self.llamadas_ocultar = 0

    def existe_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        return self.existe

    def ocultar_recurso(self, recurso_tipo: str, recurso_id: str) -> bool:
        self.llamadas_ocultar += 1
        return self.oculta


@dataclass
class RepoAuditoriaFake:
    eventos: list[EventoAuditoriaSeguridad]

    def registrar(self, evento: EventoAuditoriaSeguridad) -> None:
        self.eventos.append(evento)


def _reporte_pendiente() -> ReporteContenido:
    return ReporteContenido(
        reporte_id="rep-1",
        denunciante_id="u-1",
        recurso_tipo="publicacion",
        recurso_id="pub-1",
        motivo="spam",
        detalle=None,
        estado="pendiente",
        creado_en=datetime.now(timezone.utc),
    )


def test_crear_reporte_creado() -> None:
    repo_reportes = RepoReportesFake()
    caso = CrearReporteContenido(repo_reportes, RepoRecursosFake(existe=True))
    resultado = caso.ejecutar(
        denunciante_id="u-1", recurso_tipo="publicacion", recurso_id="pub-1", motivo="spam", detalle=None
    )
    assert resultado.accion == "creado"


def test_crear_reporte_idempotente_ya_existia() -> None:
    repo_reportes = RepoReportesFake()
    repo_reportes.creado = True
    caso = CrearReporteContenido(repo_reportes, RepoRecursosFake(existe=True))
    resultado = caso.ejecutar(
        denunciante_id="u-1", recurso_tipo="publicacion", recurso_id="pub-1", motivo="spam", detalle=None
    )
    assert resultado.accion == "ya_existia"


def test_crear_reporte_falla_si_recurso_no_existe() -> None:
    caso = CrearReporteContenido(RepoReportesFake(), RepoRecursosFake(existe=False))
    with pytest.raises(ErrorFuncionalReporte, match="recurso_no_encontrado"):
        caso.ejecutar(
            denunciante_id="u-1", recurso_tipo="publicacion", recurso_id="pub-1", motivo="spam", detalle=None
        )


def test_resolver_descartar() -> None:
    repo_reportes = RepoReportesFake()
    repo_reportes.por_id["rep-1"] = _reporte_pendiente()
    auditoria = RepoAuditoriaFake([])
    caso = ResolverReporteAdmin(repo_reportes, RepoRecursosFake(), auditoria)
    resultado = caso.ejecutar(admin_id="adm-1", reporte_id="rep-1", accion="descartar", comentario_admin=None)
    assert resultado.accion == "resuelto"
    assert auditoria.eventos[-1].reason_code == "descartar"


def test_resolver_ocultar_recurso_llama_ocultar() -> None:
    repo_reportes = RepoReportesFake()
    repo_reportes.por_id["rep-1"] = _reporte_pendiente()
    recursos = RepoRecursosFake(oculta=True)
    auditoria = RepoAuditoriaFake([])
    caso = ResolverReporteAdmin(repo_reportes, recursos, auditoria)
    caso.ejecutar(admin_id="adm-1", reporte_id="rep-1", accion="ocultar_recurso", comentario_admin="ok")
    assert recursos.llamadas_ocultar == 1


def test_resolver_ya_resuelto_idempotente() -> None:
    repo_reportes = RepoReportesFake()
    reporte = _reporte_pendiente()
    repo_reportes.por_id["rep-1"] = ReporteContenido(
        reporte_id=reporte.reporte_id,
        denunciante_id=reporte.denunciante_id,
        recurso_tipo=reporte.recurso_tipo,
        recurso_id=reporte.recurso_id,
        motivo=reporte.motivo,
        detalle=reporte.detalle,
        estado="resuelto",
        creado_en=reporte.creado_en,
    )
    caso = ResolverReporteAdmin(repo_reportes, RepoRecursosFake(), RepoAuditoriaFake([]))
    resultado = caso.ejecutar(admin_id="adm-1", reporte_id="rep-1", accion="descartar", comentario_admin=None)
    assert resultado.accion == "ya_resuelto"
