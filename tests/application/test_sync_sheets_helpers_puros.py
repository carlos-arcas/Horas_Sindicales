from __future__ import annotations

from app.application.use_cases.sync_sheets.helpers import (
    _build_solicitud_diffs,
    calcular_bloque_horario_solicitud,
    construir_payload_actualizacion_solicitud,
    construir_payload_insercion_solicitud,
    extraer_datos_delegada,
    normalizar_fechas_solicitud,
)


def _a_entero(valor):
    if valor in (None, ""):
        return 0
    return int(valor)


def test_extraer_datos_delegada_prioriza_campo_canonico() -> None:
    uuid_delegada, nombre = extraer_datos_delegada({"delegada_uuid": " u-1 ", "delegada_nombre": "  Ana   Perez "})
    assert uuid_delegada == "u-1"
    assert nombre == "Ana Perez"


def test_extraer_datos_delegada_usa_fallback_delegada() -> None:
    uuid_delegada, nombre = extraer_datos_delegada({"Delegada": "  Maria   Ruiz "})
    assert uuid_delegada == ""
    assert nombre == "Maria Ruiz"


def test_normalizar_fechas_solicitud_prioriza_fecha() -> None:
    fila = {"fecha": "2026-01-02", "created_at": "2026-01-01"}
    fecha, creacion = normalizar_fechas_solicitud(fila, lambda x: x)
    assert fecha == "2026-01-02"
    assert creacion == "2026-01-01"


def test_normalizar_fechas_solicitud_usa_fecha_pedida_si_no_hay_fecha() -> None:
    fila = {"fecha_pedida": "2026-01-03"}
    fecha, creacion = normalizar_fechas_solicitud(fila, lambda x: x)
    assert fecha == "2026-01-03"
    assert creacion == "2026-01-03"


def test_normalizar_fechas_solicitud_devuelve_none_en_vacio() -> None:
    fecha, creacion = normalizar_fechas_solicitud({}, lambda x: x)
    assert fecha is None
    assert creacion is None


def test_calcular_bloque_horario_solicitud_transforma_valores() -> None:
    fila = {"desde_h": "08", "desde_m": "30", "hasta_h": "10", "hasta_m": "15"}
    desde, hasta = calcular_bloque_horario_solicitud(fila, lambda h, m: int(h) * 60 + int(m))
    assert desde == 510
    assert hasta == 615


def test_calcular_bloque_horario_solicitud_admite_ceros() -> None:
    fila = {"desde_h": 0, "desde_m": 0, "hasta_h": 0, "hasta_m": 0}
    desde, hasta = calcular_bloque_horario_solicitud(fila, lambda h, m: int(h) * 60 + int(m))
    assert (desde, hasta) == (0, 0)


def test_construir_payload_insercion_completo() -> None:
    fila = {
        "completo": "1",
        "minutos_total": "90",
        "notas": "nota",
        "pdf_id": "pdf-1",
        "updated_at": "2026-01-04",
        "source_device": "equipo-1",
        "deleted": "0",
    }
    payload = construir_payload_insercion_solicitud(
        "uuid-1",
        77,
        fila,
        "2026-01-02",
        "2026-01-01",
        540,
        600,
        _a_entero,
        lambda: "ahora",
    )
    assert payload[0] == "uuid-1"
    assert payload[1] == 77
    assert payload[6] == 1
    assert payload[7] == 90
    assert payload[16] == 0


def test_construir_payload_insercion_fallback_horas_y_campos_vacios() -> None:
    fila = {"horas": "120", "completo": "", "deleted": "1", "notas": None}
    payload = construir_payload_insercion_solicitud(
        "uuid-2",
        2,
        fila,
        "2026-01-10",
        "2026-01-10",
        0,
        0,
        _a_entero,
        lambda: "2026-01-11",
    )
    assert payload[6] == 0
    assert payload[7] == 120
    assert payload[9] == ""
    assert payload[14] == "2026-01-11"
    assert payload[16] == 1


def test_construir_payload_actualizacion_completo() -> None:
    fila = {
        "completo": 1,
        "minutos_total": 30,
        "notas": "ok",
        "pdf_id": "p-2",
        "updated_at": "2026-01-12",
        "source_device": "equipo-2",
        "deleted": 0,
    }
    payload = construir_payload_actualizacion_solicitud(
        10,
        9,
        fila,
        "2026-01-02",
        "2026-01-01",
        60,
        120,
        _a_entero,
        lambda: "ahora",
    )
    assert payload[0] == 9
    assert payload[1] == "2026-01-02"
    assert payload[4] == 1
    assert payload[12] == 10


def test_construir_payload_actualizacion_horas_fallback_y_updated_por_defecto() -> None:
    fila = {"horas": "15", "deleted": "1", "notas": None}
    payload = construir_payload_actualizacion_solicitud(
        99,
        5,
        fila,
        "2026-02-02",
        "2026-02-01",
        1,
        2,
        _a_entero,
        lambda: "2026-02-03",
    )
    assert payload[4] == 0
    assert payload[5] == 15
    assert payload[6] == ""
    assert payload[9] == "2026-02-03"
    assert payload[11] == 1


def test_build_solicitud_diffs_detecta_cambios() -> None:
    encabezado = ["a", "b", "c"]
    diffs = _build_solicitud_diffs(encabezado, ("1", "2", "3"), ("1", "9", "3"))
    assert len(diffs) == 1
    assert diffs[0].field == "b"


def test_build_solicitud_diffs_sin_cambios() -> None:
    encabezado = ["a", "b"]
    diffs = _build_solicitud_diffs(encabezado, ("x", "y"), ("x", "y"))
    assert diffs == []


def test_build_solicitud_diffs_normaliza_a_string() -> None:
    encabezado = ["a"]
    diffs = _build_solicitud_diffs(encabezado, (1,), ("1",))
    assert diffs == []


def test_build_solicitud_diffs_detecta_none_vs_valor() -> None:
    encabezado = ["a"]
    diffs = _build_solicitud_diffs(encabezado, (None,), ("x",))
    assert len(diffs) == 1
    assert diffs[0].current_value == "None"
    assert diffs[0].new_value == "x"


def test_payloads_son_tuplas_con_longitud_estable() -> None:
    insercion = construir_payload_insercion_solicitud(
        "uuid",
        1,
        {},
        "2026-01-01",
        "2026-01-01",
        0,
        0,
        _a_entero,
        lambda: "ahora",
    )
    actualizacion = construir_payload_actualizacion_solicitud(
        1,
        1,
        {},
        "2026-01-01",
        "2026-01-01",
        0,
        0,
        _a_entero,
        lambda: "ahora",
    )
    assert isinstance(insercion, tuple)
    assert isinstance(actualizacion, tuple)
    assert len(insercion) == 17
    assert len(actualizacion) == 13
