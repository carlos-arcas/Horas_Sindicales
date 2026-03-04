from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

TIPOS_RECURSO_REPORTABLE = ("publicacion", "comentario")
MOTIVOS_REPORTE = ("spam", "acoso", "odio", "contenido_ilegal", "suplantacion", "otro")
ESTADOS_REPORTE = ("pendiente", "resuelto", "descartado")
ACCIONES_MODERACION = ("ninguna", "descartar", "ocultar_recurso")


class ErrorReporteDominio(ValueError):
    """Error base de validación para reportes de contenido."""


class ErrorIdentificadorVacio(ErrorReporteDominio):
    pass


class ErrorTipoRecursoInvalido(ErrorReporteDominio):
    pass


class ErrorMotivoReporteInvalido(ErrorReporteDominio):
    pass


class ErrorDetalleDemasiadoLargo(ErrorReporteDominio):
    pass


class ErrorPaginacionInvalida(ErrorReporteDominio):
    pass


@dataclass(frozen=True)
class PeticionPaginada:
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 50 or self.offset < 0:
            raise ErrorPaginacionInvalida("Paginación fuera de rango")


@dataclass(frozen=True)
class FiltroReportes:
    estado: str | None = None
    motivo: str | None = None
    recurso_tipo: str | None = None
    denunciante_id: str | None = None
    desde: datetime | None = None
    hasta: datetime | None = None

    def __post_init__(self) -> None:
        if self.estado is not None and self.estado not in ESTADOS_REPORTE:
            raise ValueError("estado_invalido")
        if self.motivo is not None and self.motivo not in MOTIVOS_REPORTE:
            raise ValueError("motivo_invalido")
        if self.recurso_tipo is not None and self.recurso_tipo not in TIPOS_RECURSO_REPORTABLE:
            raise ValueError("recurso_tipo_invalido")
        if self.denunciante_id is not None and len(self.denunciante_id.strip()) > 80:
            raise ValueError("denunciante_id_demasiado_largo")
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("rango_fechas_invalido")


@dataclass(frozen=True)
class ReporteContenido:
    reporte_id: str
    denunciante_id: str
    recurso_tipo: str
    recurso_id: str
    motivo: str
    detalle: str | None
    estado: str
    creado_en: datetime

    def __post_init__(self) -> None:
        reporte_id = self.reporte_id.strip()
        denunciante_id = self.denunciante_id.strip()
        recurso_id = self.recurso_id.strip()
        if not reporte_id or not denunciante_id or not recurso_id:
            raise ErrorIdentificadorVacio("Los identificadores no pueden estar vacíos")
        if self.recurso_tipo not in TIPOS_RECURSO_REPORTABLE:
            raise ErrorTipoRecursoInvalido(self.recurso_tipo)
        if self.motivo not in MOTIVOS_REPORTE:
            raise ErrorMotivoReporteInvalido(self.motivo)
        detalle = self.detalle.strip() if self.detalle is not None else None
        if detalle is not None and len(detalle) > 500:
            raise ErrorDetalleDemasiadoLargo("detalle_max_500")
        object.__setattr__(self, "reporte_id", reporte_id)
        object.__setattr__(self, "denunciante_id", denunciante_id)
        object.__setattr__(self, "recurso_id", recurso_id)
        object.__setattr__(self, "detalle", detalle)
