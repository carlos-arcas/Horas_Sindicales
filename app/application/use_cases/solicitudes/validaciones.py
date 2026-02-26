from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.dto import SolicitudDTO
from app.domain.services import ValidacionError
from app.domain.time_range import normalize_range, overlaps, TimeRangeValidationError
from app.application.use_cases.solicitudes.validacion_service import normalize_date
from app.domain.time_utils import parse_hhmm


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
    errores: list[str] = []

    if dto.persona_id <= 0:
        errores.append(REGLAS_OBLIGATORIAS[0].mensaje)
    if not str(dto.fecha_solicitud).strip():
        errores.append(REGLAS_OBLIGATORIAS[1].mensaje)
    if not str(dto.fecha_pedida).strip():
        errores.append(REGLAS_OBLIGATORIAS[2].mensaje)

    for campo_fecha in ("fecha_solicitud", "fecha_pedida"):
        valor = getattr(dto, campo_fecha)
        if valor:
            try:
                datetime.strptime(valor, "%Y-%m-%d")
            except ValueError:
                errores.append(f"{campo_fecha} debe tener formato YYYY-MM-DD.")

    if dto.completo:
        if dto.horas < 0:
            errores.append("Las horas no pueden ser negativas.")
    else:
        if not dto.desde or not dto.hasta:
            errores.append("Desde y hasta son obligatorios para peticiones parciales.")
        else:
            try:
                desde_min = parse_hhmm(dto.desde)
                hasta_min = parse_hhmm(dto.hasta)
                if hasta_min <= desde_min:
                    errores.append("El campo hasta debe ser mayor que desde.")
            except ValueError:
                errores.append("Desde/Hasta deben tener formato HH:MM válido.")

    if dto.horas > 24:
        errores.append("Las horas no pueden superar 24 en una sola petición.")

    if errores:
        raise ValidacionError("; ".join(errores))


def clave_duplicado_solicitud(dto: SolicitudDTO) -> tuple[int, str, str, str]:
    """Devuelve una clave estable para comparar duplicados en UI y aplicación."""
    if dto.completo:
        return dto.persona_id, normalize_date(dto.fecha_pedida), "COMPLETO", "COMPLETO"
    return (
        dto.persona_id,
        normalize_date(dto.fecha_pedida),
        str(dto.desde or ""),
        str(dto.hasta or ""),
    )


def hay_duplicado_distinto(
    solicitud: SolicitudDTO,
    existentes: list[SolicitudDTO],
    *,
    excluir_id: int | None = None,
    excluir_index: int | None = None,
) -> bool:
    """Comprueba choque de duplicado evitando contar la propia fila en edición."""
    try:
        inicio, fin = normalize_range(
            completo=solicitud.completo,
            desde=solicitud.desde,
            hasta=solicitud.hasta,
        )
    except TimeRangeValidationError:
        return False

    for idx, existente in enumerate(existentes):
        if excluir_id is not None and existente.id == excluir_id:
            continue
        if excluir_index is not None and idx == excluir_index:
            continue
        if existente.persona_id != solicitud.persona_id:
            continue
        if normalize_date(existente.fecha_pedida) != normalize_date(solicitud.fecha_pedida):
            continue
        try:
            ex_inicio, ex_fin = normalize_range(
                completo=existente.completo,
                desde=existente.desde,
                hasta=existente.hasta,
            )
        except TimeRangeValidationError:
            continue
        if overlaps(inicio, fin, ex_inicio, ex_fin):
            return True
    return False


def validar_seleccion_confirmacion(cantidad_seleccionadas: int) -> str | None:
    """Devuelve mensaje de aviso cuando se intenta confirmar sin filas seleccionadas."""
    if cantidad_seleccionadas > 0:
        return None
    return "Selecciona al menos una solicitud pendiente para confirmar y generar el PDF."
