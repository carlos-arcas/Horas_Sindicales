from __future__ import annotations

from datetime import datetime, timezone

from app.application.use_cases import sync_sheets_core


def test_normalize_date_accepts_supported_formats() -> None:
    assert sync_sheets_core.normalize_date("2024-05-09") == "2024-05-09"
    assert sync_sheets_core.normalize_date("09/05/24") == "2024-05-09"
    assert sync_sheets_core.normalize_date("09/05/2024") == "2024-05-09"


def test_normalize_date_handles_empty_and_invalid() -> None:
    assert sync_sheets_core.normalize_date(None) is None
    assert sync_sheets_core.normalize_date(" ") is None
    assert sync_sheets_core.normalize_date("2024/05/09") is None


def test_normalize_remote_solicitud_row_maps_aliases_and_historico_estado() -> None:
    row = {
        "uuid": "abc",
        "delegado_uuid": "del-1",
        "Delegada": "Marta",
        "fecha_pedida": "10/01/2024",
        "hora_desde": "9:5",
        "hora_hasta": "11:30",
        "horas": "120",
        "estado": "",
    }

    normalized = sync_sheets_core.normalize_remote_solicitud_row(row, "Historico")

    assert normalized["uuid"] == "abc"
    assert normalized["delegada_uuid"] == "del-1"
    assert normalized["delegada_nombre"] == "Marta"
    assert normalized["fecha"] == "2024-01-10"
    assert normalized["desde_h"] == 9
    assert normalized["desde_m"] == 5
    assert normalized["hasta_h"] == 11
    assert normalized["hasta_m"] == 30
    assert normalized["minutos_total"] == 120
    assert normalized["estado"] == "historico"


def test_normalize_remote_solicitud_row_prefers_explicit_estado_lowercased() -> None:
    normalized = sync_sheets_core.normalize_remote_solicitud_row({"estado": " APROBADA "}, "Histórico")
    assert normalized["estado"] == "aprobada"


def test_remote_hhmm_uses_full_value_and_fallback() -> None:
    assert sync_sheets_core.remote_hhmm("1", "2", "09:30") == "09:30"
    assert sync_sheets_core.remote_hhmm("9", "5", "") == "09:05"
    assert sync_sheets_core.remote_hhmm(None, None, "") is None


def test_solicitud_dedupe_key_happy_path_partial_shift() -> None:
    key = sync_sheets_core.solicitud_dedupe_key("del-1", None, "2024-01-15", False, "120", 540, 660)
    assert key == ("uuid:del-1", "2024-01-15", False, 120, 540, 660)


def test_solicitud_dedupe_key_full_day_ignores_range() -> None:
    key = sync_sheets_core.solicitud_dedupe_key("del-1", None, "2024-01-15", True, "480", 60, 600)
    assert key == ("uuid:del-1", "2024-01-15", True, 480, None, None)


def test_solicitud_dedupe_key_missing_identity_or_date_returns_none() -> None:
    assert sync_sheets_core.solicitud_dedupe_key(None, None, "2024-01-15", False, 10, 10, 20) is None
    assert sync_sheets_core.solicitud_dedupe_key("del-1", None, None, False, 10, 10, 20) is None


def test_dedupe_from_remote_normalizes_hhmm_and_matches_equivalent_rows() -> None:
    row_a = {
        "delegada_uuid": "del-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": "120",
        "desde_h": "09:00",
        "desde_m": "",
        "hasta_h": "11:00",
        "hasta_m": "",
    }
    row_b = {
        "delegada_uuid": "del-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": 120,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "11",
        "hasta_m": "0",
    }
    assert sync_sheets_core.solicitud_dedupe_key_from_remote_row(row_a) == sync_sheets_core.solicitud_dedupe_key_from_remote_row(row_b)


def test_dedupe_from_remote_detects_divergent_payload_for_same_identity() -> None:
    base = {
        "delegada_uuid": "del-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "11",
        "hasta_m": "0",
    }
    key_120 = sync_sheets_core.solicitud_dedupe_key_from_remote_row({**base, "minutos_total": "120"})
    key_180 = sync_sheets_core.solicitud_dedupe_key_from_remote_row({**base, "minutos_total": "180"})
    assert key_120 != key_180


def test_solicitud_dedupe_key_from_local_row_uses_persona_id_when_uuid_missing() -> None:
    row = {
        "persona_id": 44,
        "fecha_pedida": "2024-02-03",
        "completo": 0,
        "horas_solicitadas_min": 180,
        "desde_min": 600,
        "hasta_min": 780,
    }
    assert sync_sheets_core.solicitud_dedupe_key_from_local_row(row) == ("id:44", "2024-02-03", False, 180, 600, 780)


def test_is_conflict_only_when_both_sides_updated_after_last_sync() -> None:
    remote = datetime(2024, 1, 10, 11, 0, tzinfo=timezone.utc)
    assert sync_sheets_core.is_conflict("2024-01-10T10:00:00+00:00", remote, "2024-01-10T09:00:00+00:00")
    assert not sync_sheets_core.is_conflict("2024-01-10T08:00:00+00:00", remote, "2024-01-10T09:00:00+00:00")


def test_is_remote_newer_and_after_last_sync_rules() -> None:
    remote = datetime(2024, 1, 10, 10, 0, tzinfo=timezone.utc)
    assert sync_sheets_core.is_remote_newer("2024-01-10T09:00:00+00:00", remote)
    assert not sync_sheets_core.is_remote_newer("2024-01-10T11:00:00+00:00", remote)
    assert sync_sheets_core.is_after_last_sync("2024-01-10T11:00:00+00:00", "2024-01-10T10:00:00+00:00")
    assert not sync_sheets_core.is_after_last_sync("invalid", "2024-01-10T10:00:00+00:00")


def test_idempotence_for_merge_core_normalization_and_key_derivation() -> None:
    raw_row = {
        "delegado_uuid": "del-77",
        "delegada": " Ana ",
        "fecha": "07/02/24",
        "desde": "08:00",
        "hasta": "10:00",
        "completo": "0",
        "minutos_total": "120",
    }
    first = sync_sheets_core.normalize_remote_solicitud_row(raw_row, "solicitudes")
    second = sync_sheets_core.normalize_remote_solicitud_row(first, "solicitudes")
    assert second == first

    key_first = sync_sheets_core.solicitud_dedupe_key_from_remote_row(first)
    key_second = sync_sheets_core.solicitud_dedupe_key_from_remote_row(second)
    assert key_first == key_second


def test_canonical_remote_solicitud_person_fields_supports_legacy_aliases() -> None:
    row = {"delegado_uuid": "del-99", "delegado_nombre": "Laura"}
    delegada_uuid, delegada_nombre = sync_sheets_core.canonical_remote_solicitud_person_fields(row)
    assert delegada_uuid == "del-99"
    assert delegada_nombre == "Laura"


def test_canonical_remote_solicitud_time_parts_normalizes_hhmm() -> None:
    row = {"desde": "9:5", "hasta_h": "11", "hasta_m": "30"}
    assert sync_sheets_core.canonical_remote_solicitud_time_parts(row) == (9, 5, 11, 30)


def test_canonical_remote_solicitud_estado_handles_historico_default() -> None:
    assert sync_sheets_core.canonical_remote_solicitud_estado({"estado": ""}, "Histórico") == "historico"
    assert sync_sheets_core.canonical_remote_solicitud_estado({"estado": " APROBADA "}, "Histórico") == "aprobada"
