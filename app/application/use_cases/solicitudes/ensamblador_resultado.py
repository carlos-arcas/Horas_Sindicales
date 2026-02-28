from __future__ import annotations

from app.application.dto import ResultadoCrearSolicitudDTO, SaldosDTO, SolicitudDTO


def ensamblar_resultado_creacion(
    *,
    success: bool,
    warnings: list[str],
    errores: list[str],
    entidad: SolicitudDTO | None,
    saldos: SaldosDTO | None,
) -> ResultadoCrearSolicitudDTO:
    return ResultadoCrearSolicitudDTO(
        success=success,
        warnings=list(warnings),
        errores=list(errores),
        entidad=entidad,
        saldos=saldos,
    )
