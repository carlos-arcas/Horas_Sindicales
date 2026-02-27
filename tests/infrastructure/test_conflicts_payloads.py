from __future__ import annotations

from app.infrastructure.conflicts_payloads import (
    apply_mark_dirty,
    build_cuadrante_data_local,
    build_cuadrante_data_remote,
    build_persona_cuad_fields,
    build_persona_data_local,
    build_persona_data_remote,
    build_solicitud_data_local,
    build_solicitud_data_remote,
    solicitud_insert_params,
    solicitud_update_params,
)


def _to_int(value):
    if value in (None, ""):
        return 0
    return int(value)


def _join_min(h, m):
    if h is None and m is None:
        return None
    return _to_int(h) * 60 + _to_int(m)


def test_apply_mark_dirty_no_modifica_si_flag_false() -> None:
    data = {"updated_at": "old", "source_device": "s1"}
    assert apply_mark_dirty(data, mark_dirty=False, device_id="nuevo", now_iso="now") == data


def test_apply_mark_dirty_reemplaza_updated_y_source_device() -> None:
    data = {"updated_at": "old", "source_device": "s1", "otro": 1}
    marcado = apply_mark_dirty(data, mark_dirty=True, device_id="nuevo", now_iso="now")
    assert marcado["updated_at"] == "now"
    assert marcado["source_device"] == "nuevo"
    assert marcado["otro"] == 1


def test_build_persona_data_remote_deleted_forza_inactiva() -> None:
    data = build_persona_data_remote({"deleted": "1", "activa": "1"}, _to_int, "now")
    assert data["is_active"] == 0
    assert data["deleted"] == 1


def test_build_persona_data_remote_activa_sin_deleted() -> None:
    data = build_persona_data_remote({"activa": "1"}, _to_int, "now")
    assert data["is_active"] == 1
    assert data["updated_at"] == "now"


def test_build_persona_data_local_is_active_por_defecto() -> None:
    data = build_persona_data_local({}, _to_int, "now")
    assert data["is_active"] == 1
    assert data["horas_mes_min"] == 0


def test_build_persona_data_local_respeta_updated_at() -> None:
    data = build_persona_data_local({"updated_at": "custom"}, _to_int, "now")
    assert data["updated_at"] == "custom"


def test_build_persona_cuad_fields_devuelve_14_campos() -> None:
    fields = build_persona_cuad_fields({}, _to_int)
    assert len(fields) == 14
    assert all(value == 0 for value in fields.values())


def test_build_persona_cuad_fields_convierte_a_entero() -> None:
    fields = build_persona_cuad_fields({"cuad_lun_man_min": "30", "cuad_dom_tar_min": "90"}, _to_int)
    assert fields["cuad_lun_man_min"] == 30
    assert fields["cuad_dom_tar_min"] == 90


def test_build_solicitud_data_remote_transforma_horas_y_flags() -> None:
    data = build_solicitud_data_remote(
        {
            "fecha": "2026-01-01",
            "desde_h": "8",
            "desde_m": "30",
            "hasta_h": "10",
            "hasta_m": "00",
            "completo": "1",
            "minutos_total": "90",
            "pdf_id": "pdf",
        },
        persona_id=7,
        join_minutes=_join_min,
        int_or_zero=_to_int,
        now_iso="now",
    )
    assert data["persona_id"] == 7
    assert data["desde_min"] == 510
    assert data["hasta_min"] == 600
    assert data["completo"] == 1
    assert data["pdf_hash"] == "pdf"


def test_build_solicitud_data_remote_campos_opcionales_vacios() -> None:
    data = build_solicitud_data_remote({"fecha": "2026-01-01"}, 3, _join_min, _to_int, "now")
    assert data["notas"] == ""
    assert data["deleted"] == 0
    assert data["updated_at"] == "now"


def test_build_solicitud_data_local_usa_fechas_locales() -> None:
    data = build_solicitud_data_local({"fecha_pedida": "2026-02-02", "created_at": "2026-02-01"}, _to_int, "now")
    assert data["fecha_pedida"] == "2026-02-02"
    assert data["created_at"] == "2026-02-01"


def test_build_solicitud_data_local_normaliza_nulos() -> None:
    data = build_solicitud_data_local({"persona_id": None, "notas": None, "pdf_hash": None}, _to_int, "now")
    assert data["persona_id"] == 0
    assert data["notas"] == ""
    assert data["pdf_hash"] == ""


def test_solicitud_update_params_orden_estable() -> None:
    data = {
        "persona_id": 1,
        "fecha_pedida": "f",
        "desde_min": 1,
        "hasta_min": 2,
        "completo": 0,
        "horas_solicitadas_min": 3,
        "notas": "n",
        "pdf_hash": "p",
        "created_at": "c",
        "updated_at": "u",
        "source_device": "d",
        "deleted": 1,
    }
    params = solicitud_update_params(data, 99)
    assert params[0] == 1
    assert params[-1] == 99
    assert len(params) == 13


def test_solicitud_insert_params_incluye_nulls_internos() -> None:
    data = {
        "persona_id": 1,
        "fecha_pedida": "f",
        "desde_min": 1,
        "hasta_min": 2,
        "completo": 0,
        "horas_solicitadas_min": 3,
        "notas": "n",
        "pdf_hash": "p",
        "created_at": "c",
        "updated_at": "u",
        "source_device": "d",
        "deleted": 1,
    }
    params = solicitud_insert_params("u1", data)
    assert params[0] == "u1"
    assert params[8] is None
    assert params[10] is None
    assert len(params) == 16


def test_build_cuadrante_data_remote_convierte_bloques() -> None:
    data = build_cuadrante_data_remote({"man_h": "1", "man_m": "30", "tar_h": "2", "tar_m": "0"}, _join_min, _to_int, "now")
    assert data["man_min"] == 90
    assert data["tar_min"] == 120


def test_build_cuadrante_data_remote_updated_at_fallback() -> None:
    data = build_cuadrante_data_remote({}, _join_min, _to_int, "now")
    assert data["updated_at"] == "now"
    assert data["deleted"] == 0


def test_build_cuadrante_data_local_convierte_enteros() -> None:
    data = build_cuadrante_data_local({"man_min": "15", "tar_min": "20", "deleted": "1"}, _to_int, "now")
    assert data["man_min"] == 15
    assert data["tar_min"] == 20
    assert data["deleted"] == 1


def test_build_cuadrante_data_local_con_nulos() -> None:
    data = build_cuadrante_data_local({}, _to_int, "now")
    assert data["man_min"] == 0
    assert data["tar_min"] == 0
    assert data["updated_at"] == "now"
