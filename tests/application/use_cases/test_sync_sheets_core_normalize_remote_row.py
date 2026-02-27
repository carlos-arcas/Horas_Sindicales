from __future__ import annotations

from app.application.use_cases.sync_sheets_core import normalize_remote_solicitud_row


def test_normalize_remote_row_complete_payload() -> None:
    row = {
        "uuid": "sol-1",
        "delegada_uuid": "del-2",
        "delegada_nombre": "Ana",
        "fecha": "2024-05-09",
        "desde": "09:15",
        "hasta": "12:00",
        "desde_h": "9",
        "desde_m": "15",
        "hasta_h": "12",
        "hasta_m": "0",
        "completo": "0",
        "minutos_total": "165",
        "horas": "999",
        "notas": "detalle",
        "estado": "APROBADA",
        "created_at": "2024-05-01",
        "updated_at": "2024-05-02",
        "source_device": "movil",
        "deleted": "0",
        "pdf_id": "pdf-1",
    }

    normalized = normalize_remote_solicitud_row(row, "Solicitudes")

    assert normalized == {
        "uuid": "sol-1",
        "delegada_uuid": "del-2",
        "delegada_nombre": "Ana",
        "fecha": "2024-05-09",
        "desde": "09:15",
        "hasta": "12:00",
        "desde_h": 9,
        "desde_m": 15,
        "hasta_h": 12,
        "hasta_m": 0,
        "completo": "0",
        "minutos_total": "165",
        "horas": "999",
        "notas": "detalle",
        "estado": "aprobada",
        "created_at": "2024-05-01",
        "updated_at": "2024-05-02",
        "source_device": "movil",
        "deleted": "0",
        "pdf_id": "pdf-1",
    }


def test_normalize_remote_row_with_empty_and_none_values() -> None:
    row = {
        "uuid": None,
        "delegada_uuid": None,
        "delegada_nombre": None,
        "fecha": None,
        "created_at": None,
        "updated_at": None,
        "estado": None,
        "desde": None,
        "hasta": None,
        "desde_h": None,
        "desde_m": None,
        "hasta_h": None,
        "hasta_m": None,
        "completo": None,
        "minutos_total": None,
        "horas": None,
        "notas": None,
        "source_device": None,
        "deleted": None,
        "pdf_id": None,
    }

    normalized = normalize_remote_solicitud_row(row, "Solicitudes")

    assert normalized["uuid"] == ""
    assert normalized["delegada_uuid"] == ""
    assert normalized["delegada_nombre"] == ""
    assert normalized["fecha"] == ""
    assert normalized["created_at"] == ""
    assert normalized["updated_at"] == ""
    assert normalized["estado"] == "none"
    assert normalized["desde_h"] == ""
    assert normalized["desde_m"] == ""
    assert normalized["hasta_h"] == ""
    assert normalized["hasta_m"] == ""
    assert normalized["minutos_total"] == ""


def test_normalize_remote_row_normalizes_distinct_date_formats() -> None:
    row_one = normalize_remote_solicitud_row({"fecha": "09/05/24", "created_at": "10/05/2024"}, "Solicitudes")
    row_two = normalize_remote_solicitud_row({"fecha_pedida": "09/05/2024"}, "Solicitudes")

    assert row_one["fecha"] == "2024-05-09"
    assert row_one["created_at"] == "2024-05-10"
    assert row_two["fecha"] == "2024-05-09"
    assert row_two["created_at"] == "2024-05-09"


def test_normalize_remote_row_numbers_as_strings() -> None:
    row = {
        "hora_desde": "9:5",
        "hora_hasta": "11:30",
        "horas": "120",
        "minutos_total": "",
        "completo": "1",
    }

    normalized = normalize_remote_solicitud_row(row, "Solicitudes")

    assert normalized["desde_h"] == 9
    assert normalized["desde_m"] == 5
    assert normalized["hasta_h"] == 11
    assert normalized["hasta_m"] == 30
    assert normalized["minutos_total"] == 120
    assert normalized["completo"] == "1"
