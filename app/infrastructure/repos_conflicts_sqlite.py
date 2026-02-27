from __future__ import annotations

import json
import sqlite3

from app.application.ports.conflicts_repository import ConflictRecord
from datetime import datetime, timezone
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


def _execute_with_validation(cursor: sqlite3.Cursor, sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, params)


class SQLiteConflictsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_conflicts(self) -> list[ConflictRecord]:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at
            FROM conflicts
            ORDER BY detected_at ASC
            """
        )
        conflicts: list[ConflictRecord] = []
        for row in cursor.fetchall():
            conflicts.append(
                ConflictRecord(
                    id=row["id"],
                    uuid=row["uuid"],
                    entity_type=row["entity_type"],
                    local_snapshot=json.loads(row["local_snapshot_json"] or "{}"),
                    remote_snapshot=json.loads(row["remote_snapshot_json"] or "{}"),
                    detected_at=row["detected_at"],
                )
            )
        return conflicts

    def count_conflicts(self) -> int:
        cursor = self._connection.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM conflicts")
        row = cursor.fetchone()
        return int(row["total"] if row else 0)

    def resolve_conflict(self, conflict_id: int, keep_local: bool, device_id: str) -> bool:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, entity_type, local_snapshot_json, remote_snapshot_json
            FROM conflicts
            WHERE id = ?
            """,
            (conflict_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        local_snapshot = json.loads(row["local_snapshot_json"] or "{}")
        remote_snapshot = json.loads(row["remote_snapshot_json"] or "{}")
        self._apply_resolution(row["entity_type"], row["uuid"], local_snapshot, remote_snapshot, keep_local, device_id)
        cursor.execute("DELETE FROM conflicts WHERE id = ?", (conflict_id,))
        self._connection.commit()
        return True

    def _apply_resolution(
        self,
        entity_type: str,
        uuid_value: str,
        local_snapshot: dict,
        remote_snapshot: dict,
        keep_local: bool,
        device_id: str,
    ) -> None:
        snapshot = local_snapshot if keep_local else remote_snapshot
        mark_dirty = keep_local
        if entity_type == "delegadas":
            self._apply_persona(uuid_value, snapshot, mark_dirty, remote=not keep_local, device_id=device_id)
        elif entity_type == "solicitudes":
            self._apply_solicitud(uuid_value, snapshot, mark_dirty, remote=not keep_local, device_id=device_id)
        elif entity_type == "cuadrantes":
            self._apply_cuadrante(uuid_value, snapshot, mark_dirty, remote=not keep_local, device_id=device_id)

    def _apply_persona(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool, device_id: str) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM personas WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        persona_id = row["id"] if row else None
        if remote:
            data = build_persona_data_remote(snapshot, self._int_or_zero, self._now_iso())
            cuad_fields = {}
        else:
            data = build_persona_data_local(snapshot, self._int_or_zero, self._now_iso())
            cuad_fields = build_persona_cuad_fields(snapshot, self._int_or_zero)
        data = apply_mark_dirty(data, mark_dirty, device_id, self._now_iso())
        if persona_id:
            _execute_with_validation(
                cursor,
                """
                UPDATE personas
                SET nombre = ?, genero = ?, horas_mes_min = ?, horas_ano_min = ?, is_active = ?,
                    updated_at = ?, source_device = ?, deleted = ?
                WHERE id = ?
                """,
                (
                    data["nombre"],
                    data["genero"],
                    data["horas_mes_min"],
                    data["horas_ano_min"],
                    data["is_active"],
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                    persona_id,
                ),
                "personas.update",
            )
            if cuad_fields:
                _execute_with_validation(
                    cursor,
                    """
                    UPDATE personas
                    SET cuad_lun_man_min = ?, cuad_lun_tar_min = ?, cuad_mar_man_min = ?, cuad_mar_tar_min = ?,
                        cuad_mie_man_min = ?, cuad_mie_tar_min = ?, cuad_jue_man_min = ?, cuad_jue_tar_min = ?,
                        cuad_vie_man_min = ?, cuad_vie_tar_min = ?, cuad_sab_man_min = ?, cuad_sab_tar_min = ?,
                        cuad_dom_man_min = ?, cuad_dom_tar_min = ?
                    WHERE id = ?
                    """,
                    (
                        cuad_fields["cuad_lun_man_min"],
                        cuad_fields["cuad_lun_tar_min"],
                        cuad_fields["cuad_mar_man_min"],
                        cuad_fields["cuad_mar_tar_min"],
                        cuad_fields["cuad_mie_man_min"],
                        cuad_fields["cuad_mie_tar_min"],
                        cuad_fields["cuad_jue_man_min"],
                        cuad_fields["cuad_jue_tar_min"],
                        cuad_fields["cuad_vie_man_min"],
                        cuad_fields["cuad_vie_tar_min"],
                        cuad_fields["cuad_sab_man_min"],
                        cuad_fields["cuad_sab_tar_min"],
                        cuad_fields["cuad_dom_man_min"],
                        cuad_fields["cuad_dom_tar_min"],
                        persona_id,
                    ),
                    "personas.update_cuadrantes",
                )
        else:
            _execute_with_validation(
                cursor,
                """
                INSERT INTO personas (
                    uuid, nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min, is_active,
                    cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                    cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                    cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                    cuad_dom_man_min, cuad_dom_tar_min,
                    updated_at, source_device, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid_value,
                    data["nombre"],
                    data["genero"],
                    data["horas_mes_min"],
                    data["horas_ano_min"],
                    0,
                    data["is_active"],
                    cuad_fields.get("cuad_lun_man_min", 0),
                    cuad_fields.get("cuad_lun_tar_min", 0),
                    cuad_fields.get("cuad_mar_man_min", 0),
                    cuad_fields.get("cuad_mar_tar_min", 0),
                    cuad_fields.get("cuad_mie_man_min", 0),
                    cuad_fields.get("cuad_mie_tar_min", 0),
                    cuad_fields.get("cuad_jue_man_min", 0),
                    cuad_fields.get("cuad_jue_tar_min", 0),
                    cuad_fields.get("cuad_vie_man_min", 0),
                    cuad_fields.get("cuad_vie_tar_min", 0),
                    cuad_fields.get("cuad_sab_man_min", 0),
                    cuad_fields.get("cuad_sab_tar_min", 0),
                    cuad_fields.get("cuad_dom_man_min", 0),
                    cuad_fields.get("cuad_dom_tar_min", 0),
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                ),
                "personas.insert",
            )

    def _apply_solicitud(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool, device_id: str) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM solicitudes WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        solicitud_id = row["id"] if row else None
        if remote:
            persona_id = self._persona_id_from_uuid(snapshot.get("delegada_uuid"))
            if persona_id is None:
                raise RuntimeError("Delegada no encontrada para aplicar solicitud remota.")
            data = build_solicitud_data_remote(snapshot, persona_id, self._join_minutes, self._int_or_zero, self._now_iso())
        else:
            data = build_solicitud_data_local(snapshot, self._int_or_zero, self._now_iso())
        data = apply_mark_dirty(data, mark_dirty, device_id, self._now_iso())
        if solicitud_id:
            _execute_with_validation(
                cursor,
                """
                UPDATE solicitudes
                SET persona_id = ?, fecha_pedida = ?, desde_min = ?, hasta_min = ?, completo = ?,
                    horas_solicitadas_min = ?, notas = ?, pdf_hash = ?, created_at = ?, updated_at = ?,
                    source_device = ?, deleted = ?
                WHERE id = ?
                """,
                solicitud_update_params(data, solicitud_id),
                "solicitudes.update",
            )
        else:
            _execute_with_validation(
                cursor,
                """
                INSERT INTO solicitudes (
                    uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                    horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash,
                    created_at, updated_at, source_device, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                solicitud_insert_params(uuid_value, data),
                "solicitudes.insert",
            )

    def _apply_cuadrante(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool, device_id: str) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM cuadrantes WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        cuadrante_id = row["id"] if row else None
        if remote:
            data = build_cuadrante_data_remote(snapshot, self._join_minutes, self._int_or_zero, self._now_iso())
        else:
            data = build_cuadrante_data_local(snapshot, self._int_or_zero, self._now_iso())
        data = apply_mark_dirty(data, mark_dirty, device_id, self._now_iso())
        if cuadrante_id:
            cursor.execute(
                """
                UPDATE cuadrantes
                SET delegada_uuid = ?, dia_semana = ?, man_min = ?, tar_min = ?, updated_at = ?, source_device = ?,
                    deleted = ?
                WHERE id = ?
                """,
                (
                    data["delegada_uuid"],
                    data["dia_semana"],
                    data["man_min"],
                    data["tar_min"],
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                    cuadrante_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO cuadrantes (
                    uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid_value,
                    data["delegada_uuid"],
                    data["dia_semana"],
                    data["man_min"],
                    data["tar_min"],
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                ),
            )
        self._apply_cuadrante_to_persona(data["delegada_uuid"], data["dia_semana"], data["man_min"], data["tar_min"])

    def _apply_cuadrante_to_persona(self, delegada_uuid: str | None, dia_semana: str | None, man_min: int, tar_min: int) -> None:
        if not delegada_uuid or not dia_semana:
            return
        dia = self._normalize_dia(str(dia_semana))
        if not dia:
            return
        persona_id = self._persona_id_from_uuid(delegada_uuid)
        if persona_id is None:
            return
        cursor = self._connection.cursor()
        sql = f"""
            UPDATE personas
            SET cuad_{dia}_man_min = ?, cuad_{dia}_tar_min = ?
            WHERE id = ?
            """
        _execute_with_validation(cursor, sql, (man_min or 0, tar_min or 0, persona_id), "personas.update_cuadrante")

    def _persona_id_from_uuid(self, delegada_uuid: str | None) -> int | None:
        if not delegada_uuid:
            return None
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM personas WHERE uuid = ?", (delegada_uuid,))
        row = cursor.fetchone()
        if not row:
            return None
        return row["id"]

    @staticmethod
    def _int_or_zero(value) -> int:
        try:
            if value is None or value == "":
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _join_minutes(hours, minutes) -> int | None:
        if hours is None and minutes is None:
            return None
        return SQLiteConflictsRepository._int_or_zero(hours) * 60 + SQLiteConflictsRepository._int_or_zero(minutes)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _normalize_dia(dia: str) -> str | None:
        value = dia.strip().lower()
        mapping = {
            "lunes": "lun",
            "martes": "mar",
            "miercoles": "mie",
            "miércoles": "mie",
            "jueves": "jue",
            "viernes": "vie",
            "sabado": "sab",
            "sábado": "sab",
            "domingo": "dom",
        }
        if value in mapping:
            return mapping[value]
        if value in {"lun", "mar", "mie", "jue", "vie", "sab", "dom"}:
            return value
        return None
