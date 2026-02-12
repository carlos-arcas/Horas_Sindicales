from __future__ import annotations

from app.domain.services import BusinessRuleError
from app.domain.time_utils import parse_hhmm


def validate_request_inputs(
    desde: str | None,
    hasta: str | None,
    completo: bool,
) -> dict[str, str]:
    """Valida coherencia básica de formulario para solicitudes.

    Devuelve errores de UI por campo para permitir validación inline sin
    depender de popups.
    """

    errors: dict[str, str] = {}
    if completo:
        return errors
    if not desde:
        errors["desde"] = "La hora desde es obligatoria."
    if not hasta:
        errors["hasta"] = "La hora hasta es obligatoria."
    if errors:
        return errors
    try:
        desde_min = parse_hhmm(desde)
        hasta_min = parse_hhmm(hasta)
    except BusinessRuleError as exc:
        errors["rango"] = str(exc)
        return errors
    if desde_min > hasta_min:
        errors["rango"] = "La hora desde debe ser menor o igual que hasta."
    elif desde_min == hasta_min:
        errors["rango"] = "La solicitud parcial debe tener una duración mayor de 0 minutos."
    return errors


def compute_request_minutes(
    desde: str | None,
    hasta: str | None,
    completo: bool,
    cuadrante_base: int | None = None,
) -> int:
    """Calcula los minutos imputables de una solicitud completa o parcial.

    La regla prioriza el cuadrante base en solicitudes completas para evitar que
    dos personas con turnos distintos consuman la misma bolsa por defecto. En
    solicitudes parciales se exige un intervalo válido para impedir consumos
    negativos o nulos que distorsionen el control anual.
    """

    if completo:
        minutos = cuadrante_base or 0
        if minutos <= 0:
            raise BusinessRuleError(
                "Las horas deben ser mayores a cero. "
                "Configura el cuadrante o introduce las horas."
            )
        return minutos

    if not desde or not hasta:
        raise BusinessRuleError("Desde y hasta son obligatorios para solicitudes parciales.")
    desde_min = parse_hhmm(desde)
    hasta_min = parse_hhmm(hasta)
    if hasta_min <= desde_min:
        raise BusinessRuleError("La hora hasta debe ser mayor que desde.")
    minutos = hasta_min - desde_min
    if minutos <= 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    return minutos


def minutes_to_hours_float(minutos: int) -> float:
    """Convierte minutos a horas decimales para capas que muestran métricas.

    El dominio mantiene minutos como unidad canónica; esta conversión existe
    únicamente para presentación o interoperabilidad con DTOs históricos.
    """

    if minutos < 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    return minutos / 60.0
