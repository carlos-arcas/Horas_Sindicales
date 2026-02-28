from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.detector_duplicados import (
    ResultadoDuplicado,
    detectar_duplicado,
    detectar_duplicados_en_pendientes as _detectar_duplicados_en_pendientes,
)
from app.application.use_cases.solicitudes.normalizacion_solicitud import normalizar_solicitud
from app.application.use_cases.solicitudes.validar_datos_basicos import (
    ResultadoValidacionBasica,
    validar_datos_basicos,
)
from app.domain.services import ValidacionError


@dataclass(frozen=True)
class ReglaValidacionSolicitud:
    campo: str
    mensaje: str


REGLAS_OBLIGATORIAS: tuple[ReglaValidacionSolicitud, ...] = (
    ReglaValidacionSolicitud("persona_id", "Debe seleccionar una delegada válida."),
    ReglaValidacionSolicitud("fecha_solicitud", "La fecha de solicitud es obligatoria."),
    ReglaValidacionSolicitud("fecha_pedida", "La fecha pedida es obligatoria."),
)


def validar_solicitud_dto_declarativo(dto: SolicitudDTO) -> None:
    resultado = validar_datos_basicos(dto)
    if resultado.errores:
        raise ValidacionError("; ".join(resultado.errores))


def validar_campos_obligatorios(dto: SolicitudDTO) -> list[str]:
    return _filtrar_errores(resultado=validar_datos_basicos(dto), prefijos=tuple(r.mensaje for r in REGLAS_OBLIGATORIAS))


def validar_formato_fechas(dto: SolicitudDTO) -> list[str]:
    return _filtrar_errores(resultado=validar_datos_basicos(dto), prefijos=("fecha_solicitud", "fecha_pedida"))


def validar_regla_jornada(dto: SolicitudDTO) -> list[str]:
    prefijos = (
        "Desde y hasta son obligatorios",
        "Desde/Hasta deben tener formato",
        "El campo hasta",
        "Las horas no pueden ser negativas.",
    )
    return _filtrar_errores(resultado=validar_datos_basicos(dto), prefijos=prefijos)


def validar_jornada_completa(horas: float) -> list[str]:
    dto = _dto_dummy_para_jornada(completo=True, horas=horas)
    return validar_regla_jornada(dto)


def validar_jornada_parcial(desde: str | None, hasta: str | None) -> list[str]:
    dto = _dto_dummy_para_jornada(completo=False, horas=0.0, desde=desde, hasta=hasta)
    return validar_regla_jornada(dto)


def validar_limite_horas(horas: float) -> list[str]:
    resultado = validar_datos_basicos(_dto_dummy_para_jornada(completo=True, horas=horas))
    return [error for error in resultado.errores if error.startswith("Las horas no pueden superar")]


def clave_duplicado(dto: SolicitudDTO) -> tuple[int, str, str, str]:
    normalizada = normalizar_solicitud(dto)
    return normalizada.persona_id, normalizada.fecha, normalizada.desde, normalizada.hasta


def clave_duplicado_solicitud(dto: SolicitudDTO) -> tuple[int, str, str, str]:
    return clave_duplicado(dto)


def normalizar_clave_pendiente(dto: SolicitudDTO) -> tuple[int, str, str, str, str]:
    normalizada = normalizar_solicitud(dto)
    return normalizada.persona_id, normalizada.fecha, normalizada.desde, normalizada.hasta, normalizada.tipo


def detectar_duplicados_en_pendientes(
    pendientes: list[SolicitudDTO],
) -> set[tuple[int, str, str, str, str]]:
    return _detectar_duplicados_en_pendientes(pendientes)


def hay_duplicado_distinto(
    solicitud: SolicitudDTO,
    existentes: list[SolicitudDTO],
    *,
    excluir_por_id: str | int | None = None,
    excluir_por_indice: int | None = None,
) -> bool:
    resultado: ResultadoDuplicado = detectar_duplicado(
        solicitud,
        existentes,
        excluir_por_id=excluir_por_id,
        excluir_por_indice=excluir_por_indice,
    )
    return resultado.hay_duplicado


def validar_seleccion_confirmacion(cantidad_seleccionadas: int) -> str | None:
    if cantidad_seleccionadas > 0:
        return None
    return "Selecciona al menos una solicitud pendiente para confirmar y generar el PDF."


def _dto_dummy_para_jornada(
    *,
    completo: bool,
    horas: float,
    desde: str | None = "09:00",
    hasta: str | None = "10:00",
) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-01",
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=horas,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def _filtrar_errores(resultado: ResultadoValidacionBasica, prefijos: tuple[str, ...]) -> list[str]:
    return [error for error in resultado.errores if error.startswith(prefijos)]
