from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.infrastructure.sheets_client_puros import (
    calcular_backoff_escritura,
    calcular_backoff_lectura,
    construir_mapa_inicial_rangos,
    construir_registro,
    deduplicar_registros_por_uuid,
    extraer_nombre_hoja_de_rango,
    extraer_value_ranges,
    extraer_worksheet_desde_operacion,
    mapear_desde_diccionario,
    mapear_desde_lista,
    normalizar_fecha_iso,
    normalizar_fila,
    normalizar_hora_hhmm,
    normalizar_resultado_batch_get,
    normalizar_uuid,
    normalizar_valores_en_lista,
    resolver_spreadsheet_id,
    validar_columnas_requeridas,
)
from app.infrastructure.sheets_errors import SheetsApiCompatibilityError


def test_construir_mapa_inicial_rangos() -> None:
    assert construir_mapa_inicial_rangos(["A!A1", "B!A1"]) == {"A!A1": [], "B!A1": []}


def test_extraer_value_ranges_invalido() -> None:
    assert extraer_value_ranges({"valueRanges": "x"}) == []


def test_extraer_value_ranges_ok() -> None:
    assert extraer_value_ranges({"valueRanges": [{"range": "A!A1"}]}) == [{"range": "A!A1"}]


@pytest.mark.parametrize("valores,esperado", [([[]], [[]]), ("x", []), (None, [])])
def test_normalizar_valores_en_lista(valores, esperado) -> None:
    assert normalizar_valores_en_lista(valores) == esperado


def test_mapear_desde_diccionario_ignora_basura() -> None:
    mapped = mapear_desde_diccionario(["A!A1"], {"valueRanges": ["x", {"range": 1}, {"range": "A!A1", "values": [["1"]]}]})
    assert mapped == {"A!A1": [["1"]]}


def test_mapear_desde_lista_zippea_por_longitud_minima() -> None:
    mapped = mapear_desde_lista(["A!A1", "B!A1"], [[["1"]]])
    assert mapped == {"A!A1": [["1"]], "B!A1": []}


def test_normalizar_resultado_batch_get_dict() -> None:
    out = normalizar_resultado_batch_get(["A!A1"], {"valueRanges": [{"range": "A!A1", "values": [["x"]]}]})
    assert out["A!A1"] == [["x"]]


def test_normalizar_resultado_batch_get_list() -> None:
    out = normalizar_resultado_batch_get(["A!A1"], [[["x"]]])
    assert out["A!A1"] == [["x"]]


def test_normalizar_resultado_batch_get_error_compatibilidad() -> None:
    with pytest.raises(SheetsApiCompatibilityError):
        normalizar_resultado_batch_get(["A!A1"], "incompatible")


@pytest.mark.parametrize(
    "rango,esperado",
    [("Hoja!A1:B2", "Hoja"), ("'Mi Hoja'!A1", "Mi Hoja"), ("''", ""), ("   ", None)],
)
def test_extraer_nombre_hoja_de_rango(rango: str, esperado: str | None) -> None:
    assert extraer_nombre_hoja_de_rango(rango) == esperado


@pytest.mark.parametrize(
    "op,esperado",
    [("worksheet.get(Hoja)", "Hoja"), ("sin_parentesis", None), ("x()", None), ("x( Hoja  )", "Hoja")],
)
def test_extraer_worksheet_desde_operacion(op: str, esperado: str | None) -> None:
    assert extraer_worksheet_desde_operacion(op) == esperado


def test_resolver_spreadsheet_id_prioriza_explicito() -> None:
    assert resolver_spreadsheet_id("abc", SimpleNamespace(id="zzz")) == "abc"


def test_resolver_spreadsheet_id_desde_objeto() -> None:
    assert resolver_spreadsheet_id(None, SimpleNamespace(id="zzz")) == "zzz"


def test_resolver_spreadsheet_id_none() -> None:
    assert resolver_spreadsheet_id(None, None) is None


def test_calcular_backoff_lectura() -> None:
    assert [calcular_backoff_lectura(i) for i in range(1, 4)] == [1, 2, 4]


def test_calcular_backoff_escritura() -> None:
    assert [calcular_backoff_escritura(i) for i in range(1, 4)] == [1, 2, 4]


def test_normalizar_fila_paddea() -> None:
    assert normalizar_fila(["a"], 3) == ["a", "", ""]


def test_normalizar_fila_recorta() -> None:
    assert normalizar_fila(["a", "b", "c"], 2) == ["a", "b"]


def test_normalizar_fila_limpia_none_y_espacios() -> None:
    assert normalizar_fila([None, "  x  "], 2) == ["", "x"]


def test_normalizar_fila_total_columnas_negativo() -> None:
    with pytest.raises(ValueError):
        normalizar_fila([], -1)


def test_validar_columnas_requeridas_detecta_faltantes() -> None:
    faltan = validar_columnas_requeridas([" uuid ", "Fecha"], ["uuid", "fecha", "hora"])
    assert faltan == ["hora"]


def test_construir_registro() -> None:
    assert construir_registro(["a", "b"], [1]) == {"a": "1", "b": ""}


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("2024-01-31", "2024-01-31"),
        ("31/01/2024", "2024-01-31"),
        ("31-01-2024", "2024-01-31"),
        (date(2024, 1, 31), "2024-01-31"),
        (datetime(2024, 1, 31, 8, 30), "2024-01-31"),
        (None, None),
        ("", None),
    ],
)
def test_normalizar_fecha_iso_ok(valor, esperado) -> None:
    assert normalizar_fecha_iso(valor) == esperado


def test_normalizar_fecha_iso_error() -> None:
    with pytest.raises(ValueError):
        normalizar_fecha_iso("2024/31/01")


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("08:15", "08:15"),
        ("08:15:59", "08:15"),
        (datetime(2024, 1, 1, 9, 5), "09:05"),
        (None, None),
        ("", None),
    ],
)
def test_normalizar_hora_hhmm_ok(valor, esperado) -> None:
    assert normalizar_hora_hhmm(valor) == esperado


def test_normalizar_hora_hhmm_error() -> None:
    with pytest.raises(ValueError):
        normalizar_hora_hhmm("25:99")


@pytest.mark.parametrize(
    "valor",
    [
        "550e8400-e29b-41d4-a716-446655440000",
        "550E8400-E29B-41D4-A716-446655440000",
    ],
)
def test_normalizar_uuid_ok(valor: str) -> None:
    assert normalizar_uuid(valor) == "550e8400-e29b-41d4-a716-446655440000"


def test_normalizar_uuid_vacio() -> None:
    assert normalizar_uuid("") is None


def test_normalizar_uuid_error_tipo() -> None:
    with pytest.raises(ValueError):
        normalizar_uuid("no-es-uuid")


def test_deduplicar_registros_por_uuid() -> None:
    registros = [
        {"uuid": "550e8400-e29b-41d4-a716-446655440000", "v": 1},
        {"uuid": "550E8400-E29B-41D4-A716-446655440000", "v": 2},
        {"uuid": "", "v": 3},
    ]
    assert deduplicar_registros_por_uuid(registros) == [{"uuid": "550e8400-e29b-41d4-a716-446655440000", "v": 1}]


def test_deduplicar_registros_por_uuid_campo_custom() -> None:
    registros = [{"id": "550e8400-e29b-41d4-a716-446655440000"}]
    assert deduplicar_registros_por_uuid(registros, "id") == [{"id": "550e8400-e29b-41d4-a716-446655440000"}]


def test_deduplicar_registros_por_uuid_revienta_con_uuid_invalido() -> None:
    with pytest.raises(ValueError):
        deduplicar_registros_por_uuid([{"uuid": "malo"}])
