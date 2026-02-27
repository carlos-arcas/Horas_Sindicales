from __future__ import annotations

import sqlite3

from app.application.use_cases.sync_sheets.helpers import (
    _build_solicitud_plan_for_local_row,
    _get_persona_minutes,
    build_solicitudes_sync_plan,
    _build_solicitud_diffs,
    calcular_bloque_horario_solicitud,
    construir_payload_actualizacion_solicitud,
    construir_payload_insercion_solicitud,
    extraer_datos_delegada,
    normalizar_fechas_solicitud,
    sync_local_cuadrantes_from_personas,
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


class _FakeSyncService:
    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:")
        self._connection.row_factory = sqlite3.Row
        self.last_sync_at = "2026-01-01T00:00:00Z"
        self.now = "2026-02-01T10:00:00Z"
        self.remote_rows = [
            (3, {"uuid": "u-update", "updated_at": "2025-12-05T00:00:00Z", "raw": "remote-old"}),
            (4, {"uuid": "u-unchanged", "updated_at": "2026-01-06T00:00:00Z", "raw": "same"}),
            (5, {"uuid": "u-conflict", "updated_at": "2026-01-07T00:00:00Z", "raw": "remote-new"}),
            (6, {"uuid": "u-only-remote", "updated_at": "2026-01-10T00:00:00Z", "raw": "ghost"}),
        ]
        self._seed_schema()

    def _seed_schema(self) -> None:
        cursor = self._connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE personas (
                id INTEGER PRIMARY KEY,
                uuid TEXT,
                nombre TEXT,
                cuad_lun_man_min INTEGER,
                cuad_lun_tar_min INTEGER,
                cuad_mar_man_min INTEGER,
                cuad_mar_tar_min INTEGER,
                cuad_mie_man_min INTEGER,
                cuad_mie_tar_min INTEGER,
                cuad_jue_man_min INTEGER,
                cuad_jue_tar_min INTEGER,
                cuad_vie_man_min INTEGER,
                cuad_vie_tar_min INTEGER,
                cuad_sab_man_min INTEGER,
                cuad_sab_tar_min INTEGER,
                cuad_dom_man_min INTEGER,
                cuad_dom_tar_min INTEGER,
                updated_at TEXT
            );
            CREATE TABLE solicitudes (
                id INTEGER PRIMARY KEY,
                uuid TEXT,
                persona_id INTEGER,
                fecha_pedida TEXT,
                desde_min INTEGER,
                hasta_min INTEGER,
                completo INTEGER,
                horas_solicitadas_min INTEGER,
                notas TEXT,
                created_at TEXT,
                updated_at TEXT,
                source_device TEXT,
                deleted INTEGER,
                pdf_hash TEXT
            );
            CREATE TABLE cuadrantes (
                id INTEGER PRIMARY KEY,
                uuid TEXT,
                delegada_uuid TEXT,
                dia_semana TEXT,
                man_min INTEGER,
                tar_min INTEGER,
                updated_at TEXT,
                deleted INTEGER
            );
            """
        )
        cursor.execute(
            """
            INSERT INTO personas (
                id, uuid, nombre,
                cuad_lun_man_min, cuad_lun_tar_min,
                cuad_mar_man_min, cuad_mar_tar_min,
                cuad_mie_man_min, cuad_mie_tar_min,
                cuad_jue_man_min, cuad_jue_tar_min,
                cuad_vie_man_min, cuad_vie_tar_min,
                cuad_sab_man_min, cuad_sab_tar_min,
                cuad_dom_man_min, cuad_dom_tar_min,
                updated_at
            ) VALUES (1, 'per-1', 'Ana', 10, 20, 11, 21, 12, 22, 13, 23, 14, 24, 15, 25, 16, 26, '2026-01-01T00:00:00Z')
            """
        )
        for idx, uuid, raw, updated in [
            (1, "u-create", "local-create", "2026-01-06T00:00:00Z"),
            (2, "u-update", "local-new", "2026-01-06T00:00:00Z"),
            (3, "u-unchanged", "same", "2026-01-06T00:00:00Z"),
            (4, "u-conflict", "local-conflict", "2026-01-06T00:00:00Z"),
            (5, "", "bad-uuid", "2026-01-06T00:00:00Z"),
            (6, "u-old", "old", "2025-01-06T00:00:00Z"),
        ]:
            cursor.execute(
                """
                INSERT INTO solicitudes (
                    id, uuid, persona_id, fecha_pedida, desde_min, hasta_min,
                    completo, horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, pdf_hash
                ) VALUES (?, ?, 1, '2026-01-02', 60, 120, 1, 60, ?, '2026-01-02', ?, 'dev', 0, ?)
                """,
                (idx, uuid, raw, updated, raw),
            )
        self._connection.commit()

    def _get_worksheet(self, spreadsheet, name: str) -> str:
        assert spreadsheet == "sheet"
        assert name == "solicitudes"
        return "ws"

    def _rows_with_index(self, worksheet: str):
        assert worksheet == "ws"
        return ["uuid", "updated_at", "raw"], self.remote_rows

    def _uuid_index(self, rows):
        return {row["uuid"]: row for _, row in rows if row.get("uuid")}

    def _get_last_sync_at(self):
        return self.last_sync_at

    def _is_after_last_sync(self, updated: str | None, last_sync: str) -> bool:
        return bool(updated and updated > last_sync)

    def _parse_iso(self, value: str | None):
        return value

    def _is_conflict(self, local_updated: str | None, remote_updated: str | None, last_sync: str | None) -> bool:
        return bool(
            last_sync
            and local_updated
            and remote_updated
            and local_updated > last_sync
            and remote_updated > last_sync
            and remote_updated > local_updated
        )

    def _local_solicitud_payload(self, row):
        return (row["uuid"], row["updated_at"], row["notas"])

    def _remote_solicitud_payload(self, row):
        return (row.get("uuid"), row.get("updated_at"), row.get("raw"))

    def _now_iso(self) -> str:
        return self.now

    def _generate_uuid(self) -> str:
        return "uuid-generado"


def test_build_solicitudes_sync_plan_cubre_create_update_unchanged_conflict_y_errores() -> None:
    service = _FakeSyncService()
    plan = build_solicitudes_sync_plan(service, spreadsheet="sheet", canonical_header=["uuid", "updated_at", "raw"])

    assert plan.generated_at == "2026-02-01T10:00:00Z"
    assert [item.uuid for item in plan.to_create] == ["u-create"]
    assert [item.uuid for item in plan.to_update] == ["u-update"]
    assert [item.uuid for item in plan.unchanged] == ["u-unchanged"]
    assert [item.uuid for item in plan.conflicts] == ["u-conflict"]
    assert plan.potential_errors == ("Solicitud sin UUID: no puede sincronizarse.",)
    assert plan.values_matrix[0] == ("uuid", "updated_at", "raw")
    assert ("u-only-remote", "2026-01-10T00:00:00Z", "ghost") in plan.values_matrix


def test_build_solicitud_plan_for_local_row_descarta_si_no_supera_last_sync() -> None:
    service = _FakeSyncService()
    values: list[tuple[object, ...]] = []
    errors: list[str] = []
    row = {"uuid": "u-1", "updated_at": "2025-01-01T00:00:00Z", "notas": "x"}
    action = _build_solicitud_plan_for_local_row(service, row, {}, "2026-01-01T00:00:00Z", ["uuid", "updated_at", "raw"], values, errors)

    assert action is None
    assert values == []
    assert errors == []


def test_sync_local_cuadrantes_from_personas_inserta_y_actualiza_y_genera_uuid() -> None:
    service = _FakeSyncService()
    cursor = service._connection.cursor()
    cursor.execute(
        "INSERT INTO personas (id, uuid, nombre, cuad_lun_man_min, cuad_lun_tar_min, updated_at) VALUES (2, '', 'SinUUID', 30, 40, '2026-01-01T00:00:00Z')"
    )
    cursor.execute(
        "INSERT INTO cuadrantes (uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, deleted) VALUES ('c-1', 'per-1', 'lun', 10, 20, '2026-01-01T00:00:00Z', 0)"
    )
    service._connection.commit()

    sync_local_cuadrantes_from_personas(service)

    total = service._connection.execute("SELECT COUNT(*) AS total FROM cuadrantes").fetchone()["total"]
    assert total == 14
    lun = service._connection.execute(
        "SELECT man_min, tar_min, updated_at FROM cuadrantes WHERE delegada_uuid = 'per-1' AND dia_semana = 'lun'"
    ).fetchone()
    assert lun["man_min"] == 10
    assert lun["tar_min"] == 20
    assert lun["updated_at"] == "2026-01-01T00:00:00Z"
    nueva_uuid = service._connection.execute("SELECT uuid FROM personas WHERE id = 2").fetchone()["uuid"]
    assert nueva_uuid == "uuid-generado"


def test_get_persona_minutes_devuelve_cero_si_no_hay_valor() -> None:
    service = _FakeSyncService()
    cursor = service._connection.cursor()
    cursor.execute("UPDATE personas SET cuad_dom_tar_min = NULL WHERE id = 1")
    service._connection.commit()

    assert _get_persona_minutes(cursor, 1, "dom", "tar") == 0
