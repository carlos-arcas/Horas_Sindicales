from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.infrastructure.sheets_errors import SheetsApiCompatibilityError


def construir_mapa_inicial_rangos(rangos: list[str]) -> dict[str, list[list[str]]]:
    return {rango: [] for rango in rangos}


def extraer_value_ranges(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value_ranges = payload.get("valueRanges", [])
    return value_ranges if isinstance(value_ranges, list) else []


def normalizar_valores_en_lista(valores: Any) -> list[list[str]]:
    return valores if isinstance(valores, list) else []


def mapear_desde_diccionario(rangos: list[str], values_by_range: dict[str, Any]) -> dict[str, list[list[str]]]:
    mapped = construir_mapa_inicial_rangos(rangos)
    for value_range in extraer_value_ranges(values_by_range):
        if not isinstance(value_range, dict):
            continue
        range_name = value_range.get("range")
        if not isinstance(range_name, str):
            continue
        mapped[range_name] = normalizar_valores_en_lista(value_range.get("values", []))
    return mapped


def mapear_desde_lista(rangos: list[str], values_by_range: list[Any]) -> dict[str, list[list[str]]]:
    mapped = construir_mapa_inicial_rangos(rangos)
    for range_name, values in zip(rangos, values_by_range):
        mapped[range_name] = normalizar_valores_en_lista(values)
    return mapped


def normalizar_resultado_batch_get(rangos: list[str], values_by_range: Any) -> dict[str, list[list[str]]]:
    if isinstance(values_by_range, dict):
        return mapear_desde_diccionario(rangos, values_by_range)
    if isinstance(values_by_range, list):
        return mapear_desde_lista(rangos, values_by_range)
    raise SheetsApiCompatibilityError("Versión de gspread no soporta batch_get; usa values_batch_get")


def extraer_nombre_hoja_de_rango(range_name: str) -> str | None:
    sheet_part = range_name.split("!", 1)[0].strip() if "!" in range_name else range_name.strip()
    if not sheet_part:
        return None
    if sheet_part.startswith("'") and sheet_part.endswith("'"):
        return sheet_part[1:-1].replace("''", "'")
    return sheet_part


def extraer_worksheet_desde_operacion(operation_name: str) -> str | None:
    start = operation_name.find("(")
    end = operation_name.rfind(")")
    if start < 0 or end <= start:
        return None
    worksheet_name = operation_name[start + 1 : end].strip()
    return worksheet_name or None


def resolver_spreadsheet_id(spreadsheet_id: str | None, spreadsheet: Any | None) -> str | None:
    if spreadsheet_id:
        return spreadsheet_id
    if spreadsheet is None:
        return None
    return getattr(spreadsheet, "id", None)


def calcular_backoff_lectura(intento: int, base_segundos: int = 1) -> int:
    return base_segundos * (2 ** (intento - 1))


def calcular_backoff_escritura(intento: int) -> int:
    return 2 ** (intento - 1)


def normalizar_fila(fila: list[Any], total_columnas: int) -> list[str]:
    if total_columnas < 0:
        raise ValueError("total_columnas no puede ser negativo")
    celdas = ["" if celda is None else str(celda).strip() for celda in fila]
    if len(celdas) >= total_columnas:
        return celdas[:total_columnas]
    return celdas + [""] * (total_columnas - len(celdas))


def validar_columnas_requeridas(headers: list[str], requeridas: list[str]) -> list[str]:
    headers_norm = {header.strip().lower() for header in headers if isinstance(header, str)}
    return [col for col in requeridas if col.strip().lower() not in headers_norm]


def construir_registro(headers: list[str], fila: list[Any]) -> dict[str, str]:
    fila_normalizada = normalizar_fila(fila, len(headers))
    return {header: fila_normalizada[idx] for idx, header in enumerate(headers)}


def normalizar_fecha_iso(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Fecha inválida")


def normalizar_hora_hhmm(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M")
    texto = str(valor).strip()
    for formato in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(texto, formato).strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError("Hora inválida")


def normalizar_uuid(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    return str(UUID(str(valor).strip()))


def deduplicar_registros_por_uuid(registros: list[dict[str, Any]], campo_uuid: str = "uuid") -> list[dict[str, Any]]:
    vistos: set[str] = set()
    salida: list[dict[str, Any]] = []
    for registro in registros:
        uuid_normalizado = normalizar_uuid(registro.get(campo_uuid))
        if uuid_normalizado is None or uuid_normalizado in vistos:
            continue
        vistos.add(uuid_normalizado)
        copia = dict(registro)
        copia[campo_uuid] = uuid_normalizado
        salida.append(copia)
    return salida
