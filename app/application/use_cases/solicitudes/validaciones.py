from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.dto import SolicitudDTO
from app.domain.services import ValidacionError
from app.domain.time_range import TimeRangeValidationError
from app.application.use_cases.solicitudes.validacion_service import normalize_date
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm


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
    """Orquesta validaciones puras para mantener capa de aplicación simple y testeable.

    Mantener este método como coordinador reduce acoplamiento: las reglas de negocio
    se prueban en funciones pequeñas, sin IO, y la capa de aplicación solo agrega
    mensajes y decide si levanta la excepción.
    """

    errores: list[str] = []
    errores.extend(validar_campos_obligatorios(dto))
    errores.extend(validar_formato_fechas(dto))
    errores.extend(validar_regla_jornada(dto))
    errores.extend(validar_limite_horas(dto.horas))

    if errores:
        raise ValidacionError("; ".join(errores))


def validar_campos_obligatorios(dto: SolicitudDTO) -> list[str]:
    """Valida presencia de datos base.

    Esta función es pura y aislada; así no depende de infraestructura y se puede
    testear en milisegundos.
    """

    errores: list[str] = []
    if dto.persona_id <= 0:
        errores.append(REGLAS_OBLIGATORIAS[0].mensaje)
    if not str(dto.fecha_solicitud).strip():
        errores.append(REGLAS_OBLIGATORIAS[1].mensaje)
    if not str(dto.fecha_pedida).strip():
        errores.append(REGLAS_OBLIGATORIAS[2].mensaje)
    return errores


def validar_formato_fechas(dto: SolicitudDTO) -> list[str]:
    """Valida formato YYYY-MM-DD solo cuando el campo existe."""

    errores: list[str] = []
    for campo_fecha in ("fecha_solicitud", "fecha_pedida"):
        valor = getattr(dto, campo_fecha)
        if not valor:
            continue
        try:
            datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            errores.append(f"{campo_fecha} debe tener formato YYYY-MM-DD.")
    return errores


def validar_regla_jornada(dto: SolicitudDTO) -> list[str]:
    """Separa reglas de petición completa/parcial para reducir complejidad ciclomática."""

    if dto.completo:
        return validar_jornada_completa(dto.horas)
    return validar_jornada_parcial(dto.desde, dto.hasta)


def validar_jornada_completa(horas: float) -> list[str]:
    """Regla de negocio específica de jornadas completas."""

    if horas < 0:
        return ["Las horas no pueden ser negativas."]
    return []


def validar_jornada_parcial(desde: str | None, hasta: str | None) -> list[str]:
    """Reglas de rango horario para jornadas parciales."""

    if not desde or not hasta:
        return ["Desde y hasta son obligatorios para peticiones parciales."]

    try:
        desde_min = parse_hhmm(desde)
        hasta_min = parse_hhmm(hasta)
    except ValueError:
        return ["Desde/Hasta deben tener formato HH:MM válido."]

    if hasta_min <= desde_min:
        return ["El campo hasta debe ser mayor que desde."]
    return []


def validar_limite_horas(horas: float) -> list[str]:
    """Límite transversal independiente del tipo de jornada."""

    if horas > 24:
        return ["Las horas no pueden superar 24 en una sola petición."]
    return []


def clave_duplicado(dto: SolicitudDTO) -> tuple[int, str, str, str]:
    """Devuelve la clave lógica usada para detectar solicitudes duplicadas."""

    fecha = normalize_date(dto.fecha_pedida)
    if dto.completo:
        return dto.persona_id, fecha, "COMPLETO", "COMPLETO"

    desde = minutes_to_hhmm(parse_hhmm(str(dto.desde or "")))
    hasta = minutes_to_hhmm(parse_hhmm(str(dto.hasta or "")))
    return dto.persona_id, fecha, desde, hasta


def clave_duplicado_solicitud(dto: SolicitudDTO) -> tuple[int, str, str, str]:
    """Alias de compatibilidad para consumidores existentes."""

    return clave_duplicado(dto)


def normalizar_clave_pendiente(dto: SolicitudDTO) -> tuple[int, str, str, str, str]:
    """Normaliza la clave de negocio usada para detectar duplicados en pendientes."""

    persona_id = int(dto.persona_id)
    fecha = normalize_date(dto.fecha_pedida)
    tipo = "COMPLETO" if dto.completo else "PARCIAL"
    if dto.completo:
        return persona_id, fecha, "COMPLETO", "COMPLETO", tipo

    desde = minutes_to_hhmm(parse_hhmm(str(dto.desde or "")))
    hasta = minutes_to_hhmm(parse_hhmm(str(dto.hasta or "")))
    return persona_id, fecha, desde, hasta, tipo


def detectar_duplicados_en_pendientes(
    pendientes: list[SolicitudDTO],
) -> set[tuple[int, str, str, str, str]]:
    """Devuelve las claves de negocio repetidas (2+ veces) dentro de pendientes."""

    conteo: dict[tuple[int, str, str, str, str], int] = {}
    for pendiente in pendientes:
        try:
            clave = normalizar_clave_pendiente(pendiente)
        except (TimeRangeValidationError, ValueError):
            continue
        conteo[clave] = conteo.get(clave, 0) + 1

    return {clave for clave, repeticiones in conteo.items() if repeticiones >= 2}


def hay_duplicado_distinto(
    solicitud: SolicitudDTO,
    existentes: list[SolicitudDTO],
    *,
    excluir_por_id: str | int | None = None,
    excluir_por_indice: int | None = None,
) -> bool:
    """Comprueba choque de duplicado evitando contar la propia fila en edición."""

    try:
        clave_objetivo = clave_duplicado(solicitud)
    except (TimeRangeValidationError, ValueError):
        return False

    for idx, existente in enumerate(existentes):
        if excluir_por_id is not None and existente.id is not None and str(existente.id) == str(excluir_por_id):
            continue
        if existente.id is None and excluir_por_indice is not None and idx == excluir_por_indice:
            continue

        try:
            clave_existente = clave_duplicado(existente)
        except (TimeRangeValidationError, ValueError):
            continue
        if clave_existente == clave_objetivo:
            return True
    return False


def validar_seleccion_confirmacion(cantidad_seleccionadas: int) -> str | None:
    """Devuelve mensaje de aviso cuando se intenta confirmar sin filas seleccionadas."""
    if cantidad_seleccionadas > 0:
        return None
    return "Selecciona al menos una solicitud pendiente para confirmar y generar el PDF."
