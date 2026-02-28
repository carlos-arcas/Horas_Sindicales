from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.application.use_cases.sync_sheets.sync_snapshots import (
    build_local_solicitud_payload,
    build_pdf_log_payload,
    build_pull_signals_snapshot,
    format_rango_fechas,
    normalize_dia,
    parse_remote_solicitud_row,
    pdf_log_insert_values,
    pdf_log_update_values,
)


@pytest.mark.parametrize(
    ("raw_uuid", "expected"),
    [
        (None, ""),
        ("", ""),
        ("  abc  ", "abc"),
        (123, "123"),
    ],
)
def test_parse_remote_solicitud_row_uuid_normalization(raw_uuid, expected) -> None:
    dto = parse_remote_solicitud_row(
        {"uuid": raw_uuid, "updated_at": "2024-01-01T00:00:00Z"},
        normalize_remote_uuid=lambda value: str(value or "").strip(),
        parse_iso=lambda value: datetime(2024, 1, 1, tzinfo=timezone.utc) if value else None,
    )
    assert dto.uuid_value == expected


@pytest.mark.parametrize("has_uuid", [True, False])
def test_parse_remote_solicitud_row_parses_updated_only_with_uuid(has_uuid: bool) -> None:
    parsed = {"count": 0}

    def _parse(_: str) -> datetime:
        parsed["count"] += 1
        return datetime(2024, 1, 1, tzinfo=timezone.utc)

    parse_remote_solicitud_row(
        {"uuid": "u1" if has_uuid else "", "updated_at": "2024-01-01T00:00:00Z"},
        normalize_remote_uuid=lambda value: str(value or "").strip(),
        parse_iso=_parse,
    )
    assert parsed["count"] == (1 if has_uuid else 0)


@pytest.mark.parametrize(
    ("existing", "local", "skip_duplicate", "expected"),
    [
        (None, None, False, (False, False, False, False, False, None)),
        ({"uuid": "x"}, None, False, (True, False, False, False, False, "x")),
        (None, {"updated_at": "a"}, False, (False, True, False, True, True, None)),
        ({"uuid": "z"}, {"updated_at": "a"}, True, (True, True, True, True, True, "z")),
    ],
)
def test_build_pull_signals_snapshot(existing, local, skip_duplicate, expected) -> None:
    dto = parse_remote_solicitud_row(
        {"uuid": "u", "updated_at": "2024-01-01T00:00:00Z"},
        normalize_remote_uuid=lambda value: str(value or "").strip(),
        parse_iso=lambda value: datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    signals = build_pull_signals_snapshot(
        dto=dto,
        local_row=local,
        existing=existing,
        skip_duplicate=skip_duplicate,
        enable_backfill=True,
        is_conflict=lambda *_: True,
        is_remote_newer=lambda *_: True,
        last_sync_at="2024-01-01T00:00:00Z",
    )
    assert (
        signals.has_existing_for_empty_uuid,
        signals.has_local_uuid,
        signals.skip_duplicate,
        signals.conflict_detected,
        signals.remote_is_newer,
        signals.existing_uuid,
    ) == expected


@pytest.mark.parametrize(
    ("row", "is_none"),
    [
        ({}, True),
        ({"pdf_id": ""}, True),
        ({"pdf_id": "p1"}, False),
        ({"pdf_id": " p2 ", "hash": "h"}, False),
    ],
)
def test_build_pdf_log_payload(row, is_none: bool) -> None:
    payload = build_pdf_log_payload(row)
    assert (payload is None) is is_none


def test_pdf_log_tuple_builders_keep_order() -> None:
    payload = {
        "pdf_id": "p",
        "delegada_uuid": "d",
        "rango_fechas": "r",
        "fecha_generacion": "f",
        "hash": "h",
        "updated_at": "u",
        "source_device": "s",
    }
    assert pdf_log_insert_values(payload) == ("p", "d", "r", "f", "h", "u", "s")
    assert pdf_log_update_values(payload) == ("d", "r", "f", "h", "u", "s", "p")


@pytest.mark.parametrize(
    ("dia", "expected"),
    [
        ("lunes", "lun"),
        ("martes", "mar"),
        ("miercoles", "mie"),
        ("miércoles", "mie"),
        ("jueves", "jue"),
        ("viernes", "vie"),
        ("sabado", "sab"),
        ("sábado", "sab"),
        ("domingo", "dom"),
        (" lun ", "lun"),
        ("mar", "mar"),
        ("MIE", "mie"),
        ("jue", "jue"),
        ("vie", "vie"),
        ("sab", "sab"),
        ("dom", "dom"),
        ("", None),
        ("foo", None),
    ],
)
def test_normalize_dia(dia: str, expected: str | None) -> None:
    assert normalize_dia(dia) == expected


@pytest.mark.parametrize(
    ("fechas", "expected"),
    [
        ([], ""),
        ([""], ""),
        (["2024-01-03"], "2024-01-03"),
        (["2024-01-03", "2024-01-01"], "2024-01-01 - 2024-01-03"),
        (["2024-01-03", "2024-01-03"], "2024-01-03"),
    ],
)
def test_format_rango_fechas(fechas, expected: str) -> None:
    assert format_rango_fechas(fechas) == expected


def test_build_local_solicitud_payload_contract() -> None:
    row = {
        "uuid": "u1",
        "delegada_uuid": "d1",
        "delegada_nombre": "Delegada",
        "fecha_pedida": "2024-01-01",
        "desde_min": 60,
        "hasta_min": 120,
        "completo": 1,
        "horas_solicitadas_min": 60,
        "notas": "nota",
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02",
        "source_device": "",
        "deleted": None,
        "pdf_hash": "",
    }

    payload = build_local_solicitud_payload(
        row,
        device_id="dev-x",
        to_iso_date=lambda value: str(value),
        split_minutes=lambda value: (value // 60, value % 60),
        int_or_zero=lambda value: int(value or 0),
    )

    assert payload[0] == "u1"
    assert payload[4:8] == (1, 0, 2, 0)
    assert payload[14] == "dev-x"
