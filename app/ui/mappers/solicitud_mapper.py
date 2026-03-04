from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from app.ui.viewmodels import HistoricoSolicitudViewModel, PendienteSolicitudViewModel, SolicitudViewModel

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO


def _a_texto_fecha(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def _a_texto_horas(valor: Any) -> str:
    if valor is None:
        return "0"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return f"{valor:g}"
    return str(valor)


def _resolver_estado(dto: "SolicitudDTO") -> str:
    if getattr(dto, "generated", False):
        return "CONFIRMADA"
    return "PENDIENTE"


def dto_a_viewmodel(dto: "SolicitudDTO") -> SolicitudViewModel:
    fecha = _a_texto_fecha(getattr(dto, "fecha", None) or getattr(dto, "fecha_pedida", None))
    horas = _a_texto_horas(getattr(dto, "horas", None))
    descripcion = str(getattr(dto, "observaciones", "") or "")

    return SolicitudViewModel(
        id=int(getattr(dto, "id", 0) or 0),
        fecha=fecha,
        horas=horas,
        estado=_resolver_estado(dto),
        descripcion=descripcion,
    )


def dto_a_historico_viewmodel(dto: "SolicitudDTO") -> HistoricoSolicitudViewModel:
    fecha = _a_texto_fecha(getattr(dto, "fecha", None) or getattr(dto, "fecha_pedida", None))
    horas = _a_texto_horas(getattr(dto, "horas", None))

    return HistoricoSolicitudViewModel(
        id=int(getattr(dto, "id", 0) or 0),
        fecha=fecha,
        horas=horas,
        estado=_resolver_estado(dto),
    )


def dto_a_pendiente_viewmodel(dto: "SolicitudDTO") -> PendienteSolicitudViewModel:
    fecha = _a_texto_fecha(getattr(dto, "fecha", None) or getattr(dto, "fecha_pedida", None))
    horas = _a_texto_horas(getattr(dto, "horas", None))
    descripcion = str(getattr(dto, "observaciones", "") or "")

    return PendienteSolicitudViewModel(
        id=int(getattr(dto, "id", 0) or 0),
        fecha=fecha,
        horas=horas,
        descripcion=descripcion,
    )
