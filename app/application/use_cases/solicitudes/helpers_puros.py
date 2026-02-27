from __future__ import annotations

from dataclasses import replace

from app.application.dto import ResultadoCrearSolicitudDTO, SolicitudDTO
from app.application.use_cases.solicitudes.validacion_service import normalize_date, normalize_time


# Nota para juniors:
# Este módulo concentra lógica PURA (sin repositorio/DB/red/FS).
# Extraerla reduce acoplamiento y hace que las reglas sean fáciles de testear
# sin montar infraestructura, alineando Clean Architecture.


def resultado_error_creacion(errores: list[str], warnings: list[str]) -> ResultadoCrearSolicitudDTO:
    return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)


def mensaje_persona_invalida(persona_id: int) -> str | None:
    if persona_id <= 0:
        return "Selecciona una delegada válida antes de guardar la solicitud."
    return None


def normalizar_dto_para_creacion(dto: SolicitudDTO) -> SolicitudDTO:
    return replace(
        dto,
        fecha_pedida=normalize_date(dto.fecha_pedida),
        fecha_solicitud=normalize_date(dto.fecha_solicitud),
        desde=None if dto.desde is None else normalize_time(dto.desde),
        hasta=None if dto.hasta is None else normalize_time(dto.hasta),
    )


def mensaje_conflicto(accion_sugerida: str | None) -> str:
    return "Conflicto completo/parcial en la misma fecha. Acción sugerida: " f"{accion_sugerida}."


def mensaje_duplicado(duplicado_confirmado: bool) -> str:
    return "Duplicado confirmado" if duplicado_confirmado else "Duplicado pendiente"


def saldo_insuficiente(restantes_mes: int, restantes_ano: int, minutos_solicitados: int) -> bool:
    return restantes_mes < minutos_solicitados or restantes_ano < minutos_solicitados


def mensaje_warning_saldo_insuficiente() -> str:
    return "Saldo insuficiente. La petición se ha registrado igualmente."
