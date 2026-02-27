from __future__ import annotations

import pytest

from app.application.use_cases.sync_sheets import payloads_puros


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("", ""),
        ("  Ana   Ruiz ", "Ana Ruiz"),
        (123, "123"),
    ],
)
def test_limpiar_texto(value, expected) -> None:
    assert payloads_puros.limpiar_texto(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, ""), ("  ", ""), (" abc ", "abc")],
)
def test_valor_normalizado(value, expected) -> None:
    assert payloads_puros.valor_normalizado(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("", None), (" u-1 ", "u-1")],
)
def test_uuid_o_none(value, expected) -> None:
    assert payloads_puros.uuid_o_none(value) == expected


def test_es_fila_vacia_detecta_campos_objetivo() -> None:
    assert payloads_puros.es_fila_vacia({"uuid": "", "nombre": " "}, ("uuid", "nombre"))
    assert not payloads_puros.es_fila_vacia({"uuid": "u", "nombre": ""}, ("uuid", "nombre"))


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"delegada_uuid": "d-1"}, "d-1"),
        ({"delegado_uuid": "d-2"}, "d-2"),
        ({"persona_uuid": "d-3"}, "d-3"),
        ({}, ""),
    ],
)
def test_resolver_delegada_uuid_prioridades(row, expected) -> None:
    assert payloads_puros.resolver_delegada_uuid(row) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"delegada_nombre": " Ana  Perez "}, "Ana Perez"),
        ({"Delegada": " Marta "}, "Marta"),
        ({"delegado_nombre": "  Luis "}, "Luis"),
        ({"nombre": " Nora "}, "Nora"),
        ({}, ""),
    ],
)
def test_resolver_delegada_nombre_fallbacks(row, expected) -> None:
    assert payloads_puros.resolver_delegada_nombre(row) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-02", "2026-01-02"),
        ("02/01/2026", "2026-01-02"),
        ("02/01/26", "2026-01-02"),
        ("invalida", "invalida"),
    ],
)
def test_normalizar_fecha(value, expected) -> None:
    assert payloads_puros.normalizar_fecha(value) == expected


def test_remote_hhmm_desde_fila_toma_formato_largo() -> None:
    row = {"desde_h": "9", "desde_m": "5"}
    assert payloads_puros.remote_hhmm_desde_fila(row, "desde") == "09:05"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("09:30", (9, 30)),
        ("9:5", (9, 5)),
        (None, ("", "")),
        ("", ("", "")),
        ("invalid", ("", "")),
    ],
)
def test_hhmm_a_componentes(value, expected) -> None:
    assert payloads_puros.hhmm_a_componentes(value) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"minutos_total": "45"}, 45),
        ({"horas": "60"}, 60),
        ({}, 0),
    ],
)
def test_obtener_minutos_totales(row, expected) -> None:
    assert payloads_puros.obtener_minutos_totales(row) == expected


def test_payload_remoto_solicitud_happy_path() -> None:
    row = {
        "uuid": "u-1",
        "delegada_uuid": "d-1",
        "delegada_nombre": "Ana",
        "fecha": "2026-01-02",
        "desde": "09:00",
        "hasta": "11:30",
        "completo": "1",
        "minutos_total": "150",
        "notas": "ok",
        "estado": "pendiente",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-03",
        "source_device": "pc",
        "deleted": "0",
        "pdf_id": "p-1",
    }
    payload = payloads_puros.payload_remoto_solicitud(row)
    assert payload[0] == "u-1"
    assert payload[4:8] == (9, 0, 11, 30)
    assert payload[8] == 1
    assert payload[9] == 150


def test_payload_remoto_solicitud_fallbacks_y_nulos() -> None:
    row = {
        "delegado_uuid": "d-9",
        "Delegada": " Delegada X ",
        "fecha_pedida": "03/01/2026",
        "desde_h": "8",
        "desde_m": "1",
        "hasta_h": "9",
        "hasta_m": "2",
        "horas": "61",
        "deleted": None,
    }
    payload = payloads_puros.payload_remoto_solicitud(row)
    assert payload[1] == "d-9"
    assert payload[2] == "Delegada X"
    assert payload[3] == "2026-01-03"
    assert payload[4:8] == (8, 1, 9, 2)
    assert payload[9] == 61


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("1", 1, False),
        (None, "", False),
        ("A", "B", True),
    ],
)
def test_valores_distintos(left, right, expected) -> None:
    assert payloads_puros.valores_distintos(left, right) is expected


def test_diff_campos_detecta_cambios_parciales() -> None:
    local = {"a": "1", "b": "x", "c": "3"}
    remote = {"a": "1", "b": "y", "c": "3"}
    assert payloads_puros.diff_campos(local, remote, ("a", "b", "c")) == ("b",)


@pytest.mark.parametrize(
    ("row", "required", "ok", "msg"),
    [
        ({"uuid": "u-1", "fecha": "2026-01-01"}, ("uuid", "fecha"), True, None),
        ({"uuid": ""}, ("uuid", "fecha"), False, "Campos requeridos ausentes: uuid, fecha"),
    ],
)
def test_validar_shape_minimo(row, required, ok, msg) -> None:
    assert payloads_puros.validar_shape_minimo(row, required) == (ok, msg)


@pytest.mark.parametrize(
    ("updated", "last_sync", "expected"),
    [
        ("2026-01-02T00:00:00+00:00", None, False),
        ("2026-01-02T00:00:00+00:00", "2026-01-01T00:00:00+00:00", False),
        ("2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00", True),
    ],
)
def test_debe_omitir_por_last_sync(updated, last_sync, expected) -> None:
    assert payloads_puros.debe_omitir_por_last_sync(updated, last_sync) is expected


def test_normalizar_updated_at_usar_fallback() -> None:
    assert payloads_puros.normalizar_updated_at({"updated_at": ""}, "2026-01-01") == "2026-01-01"


@pytest.mark.parametrize(
    ("local", "remote", "expected"),
    [
        ({"a": "1"}, {"a": "1"}, False),
        ({"a": "1"}, {"a": "2"}, True),
    ],
)
def test_conflicto_por_divergencia(local, remote, expected) -> None:
    assert payloads_puros.conflicto_por_divergencia(local, remote, ("a",)) is expected


@pytest.mark.parametrize(
    ("persona_uuid", "nombre", "by_uuid", "by_nombre", "accion"),
    [
        ("u1", "Ana", {"uuid": "u1"}, None, "usar_uuid"),
        ("u2", "Ana", None, {"id": 1, "uuid": "u-local"}, "colision_nombre"),
        ("u2", "Ana", None, {"id": 2, "uuid": ""}, "asignar_uuid_por_nombre"),
        ("u3", "Ana", None, None, "insertar_uuid"),
        (None, "Ana", None, {"id": 4, "uuid": "u4"}, "usar_nombre"),
        (None, "", None, None, "insertar_generado"),
    ],
)
def test_resolver_persona_accion(persona_uuid, nombre, by_uuid, by_nombre, accion) -> None:
    plan = payloads_puros.resolver_persona_accion(persona_uuid, nombre, by_uuid, by_nombre)
    assert plan["accion"] == accion


@pytest.mark.parametrize(
    ("enabled", "original_uuid", "persona_uuid", "expected"),
    [
        (True, "", "u-1", True),
        (True, "u-old", "u-1", False),
        (False, "", "u-1", False),
        (True, "", None, False),
    ],
)
def test_requiere_backfill_uuid(enabled, original_uuid, persona_uuid, expected) -> None:
    assert payloads_puros.requiere_backfill_uuid(enabled, original_uuid, persona_uuid) is expected


@pytest.mark.parametrize(
    ("fecha", "expected"),
    [
        ("2026-01-01", True),
        ("2026-01-01T10:00:00+00:00", True),
        ("2026-01-01T10:00:00Z", True),
        ("", False),
        (None, False),
        ("01/01/2026", False),
    ],
)
def test_fecha_es_valida(fecha, expected) -> None:
    assert payloads_puros.fecha_es_valida(fecha) is expected
