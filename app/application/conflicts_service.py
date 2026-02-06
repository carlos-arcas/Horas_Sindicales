from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


def _execute_with_validation(cursor: sqlite3.Cursor, sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, params)


@dataclass(frozen=True)
class ConflictRecord:
    id: int
    uuid: str
    entity_type: str
    local_snapshot: dict
    remote_snapshot: dict
    detected_at: str


class ConflictsService:
    def __init__(self, connection: sqlite3.Connection, device_id_provider: Callable[[], str] | None = None) -> None:
        self._connection = connection
        self._device_id_provider = device_id_provider or (lambda: "")

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

    def resolve_conflict(self, conflict_id: int, keep: str) -> None:
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
            return
        local_snapshot = json.loads(row["local_snapshot_json"] or "{}")
        remote_snapshot = json.loads(row["remote_snapshot_json"] or "{}")
        keep_local = keep.lower() == "local"
        self._apply_resolution(row["entity_type"], row["uuid"], local_snapshot, remote_snapshot, keep_local)
        cursor.execute("DELETE FROM conflicts WHERE id = ?", (conflict_id,))
        self._connection.commit()

    def resolve_all_latest(self) -> int:
        conflicts = self.list_conflicts()
        if not conflicts:
            return 0
        for conflict in conflicts:
            keep_local = self._is_local_newer(conflict.local_snapshot, conflict.remote_snapshot)
            self._apply_resolution(
                conflict.entity_type,
                conflict.uuid,
                conflict.local_snapshot,
                conflict.remote_snapshot,
                keep_local,
            )
            cursor = self._connection.cursor()
            cursor.execute("DELETE FROM conflicts WHERE id = ?", (conflict.id,))
        self._connection.commit()
        return len(conflicts)

    def _apply_resolution(
        self,
        entity_type: str,
        uuid_value: str,
        local_snapshot: dict,
        remote_snapshot: dict,
        keep_local: bool,
    ) -> None:
        snapshot = local_snapshot if keep_local else remote_snapshot
        mark_dirty = keep_local
        if entity_type == "delegadas":
            self._apply_persona(uuid_value, snapshot, mark_dirty, remote=not keep_local)
        elif entity_type == "solicitudes":
            self._apply_solicitud(uuid_value, snapshot, mark_dirty, remote=not keep_local)
        elif entity_type == "cuadrantes":
            self._apply_cuadrante(uuid_value, snapshot, mark_dirty, remote=not keep_local)

    def _apply_persona(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM personas WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        persona_id = row["id"] if row else None
        if remote:
            data = {
                "nombre": snapshot.get("nombre"),
                "genero": snapshot.get("genero"),
                "horas_mes_min": self._int_or_zero(snapshot.get("bolsa_mes_min")),
                "horas_ano_min": self._int_or_zero(snapshot.get("bolsa_anual_min")),
                "is_active": 0
                if self._int_or_zero(snapshot.get("deleted"))
                else (1 if self._int_or_zero(snapshot.get("activa")) else 0),
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
            cuad_fields = {}
        else:
            data = {
                "nombre": snapshot.get("nombre"),
                "genero": snapshot.get("genero"),
                "horas_mes_min": self._int_or_zero(snapshot.get("horas_mes_min")),
                "horas_ano_min": self._int_or_zero(snapshot.get("horas_ano_min")),
                "is_active": 1 if self._int_or_zero(snapshot.get("is_active", 1)) else 0,
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
            cuad_fields = {
                "cuad_lun_man_min": self._int_or_zero(snapshot.get("cuad_lun_man_min")),
                "cuad_lun_tar_min": self._int_or_zero(snapshot.get("cuad_lun_tar_min")),
                "cuad_mar_man_min": self._int_or_zero(snapshot.get("cuad_mar_man_min")),
                "cuad_mar_tar_min": self._int_or_zero(snapshot.get("cuad_mar_tar_min")),
                "cuad_mie_man_min": self._int_or_zero(snapshot.get("cuad_mie_man_min")),
                "cuad_mie_tar_min": self._int_or_zero(snapshot.get("cuad_mie_tar_min")),
                "cuad_jue_man_min": self._int_or_zero(snapshot.get("cuad_jue_man_min")),
                "cuad_jue_tar_min": self._int_or_zero(snapshot.get("cuad_jue_tar_min")),
                "cuad_vie_man_min": self._int_or_zero(snapshot.get("cuad_vie_man_min")),
                "cuad_vie_tar_min": self._int_or_zero(snapshot.get("cuad_vie_tar_min")),
                "cuad_sab_man_min": self._int_or_zero(snapshot.get("cuad_sab_man_min")),
                "cuad_sab_tar_min": self._int_or_zero(snapshot.get("cuad_sab_tar_min")),
                "cuad_dom_man_min": self._int_or_zero(snapshot.get("cuad_dom_man_min")),
                "cuad_dom_tar_min": self._int_or_zero(snapshot.get("cuad_dom_tar_min")),
            }
        if mark_dirty:
            data["updated_at"] = self._now_iso()
            data["source_device"] = self._device_id_provider()
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

    def _apply_solicitud(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM solicitudes WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        solicitud_id = row["id"] if row else None
        if remote:
            persona_id = self._persona_id_from_uuid(snapshot.get("delegada_uuid"))
            if persona_id is None:
                raise RuntimeError("Delegada no encontrada para aplicar solicitud remota.")
            desde_min = self._join_minutes(snapshot.get("desde_h"), snapshot.get("desde_m"))
            hasta_min = self._join_minutes(snapshot.get("hasta_h"), snapshot.get("hasta_m"))
            data = {
                "persona_id": persona_id,
                "fecha_pedida": snapshot.get("fecha"),
                "desde_min": desde_min,
                "hasta_min": hasta_min,
                "completo": 1 if self._int_or_zero(snapshot.get("completo")) else 0,
                "horas_solicitadas_min": self._int_or_zero(snapshot.get("minutos_total")),
                "notas": snapshot.get("notas") or "",
                "pdf_hash": snapshot.get("pdf_id") or "",
                "created_at": snapshot.get("created_at") or snapshot.get("fecha"),
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
        else:
            data = {
                "persona_id": self._int_or_zero(snapshot.get("persona_id")),
                "fecha_pedida": snapshot.get("fecha_pedida"),
                "desde_min": snapshot.get("desde_min"),
                "hasta_min": snapshot.get("hasta_min"),
                "completo": 1 if self._int_or_zero(snapshot.get("completo")) else 0,
                "horas_solicitadas_min": self._int_or_zero(snapshot.get("horas_solicitadas_min")),
                "notas": snapshot.get("notas") or "",
                "pdf_hash": snapshot.get("pdf_hash") or "",
                "created_at": snapshot.get("created_at") or snapshot.get("fecha_pedida"),
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
        if mark_dirty:
            data["updated_at"] = self._now_iso()
            data["source_device"] = self._device_id_provider()
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
                (
                    data["persona_id"],
                    data["fecha_pedida"],
                    data["desde_min"],
                    data["hasta_min"],
                    data["completo"],
                    data["horas_solicitadas_min"],
                    data["notas"],
                    data["pdf_hash"],
                    data["created_at"],
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                    solicitud_id,
                ),
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
                (
                    uuid_value,
                    data["persona_id"],
                    data["created_at"],
                    data["fecha_pedida"],
                    data["desde_min"],
                    data["hasta_min"],
                    data["completo"],
                    data["horas_solicitadas_min"],
                    None,
                    data["notas"],
                    None,
                    data["pdf_hash"],
                    data["created_at"],
                    data["updated_at"],
                    data["source_device"],
                    data["deleted"],
                ),
                "solicitudes.insert",
            )

    def _apply_cuadrante(self, uuid_value: str, snapshot: dict, mark_dirty: bool, remote: bool) -> None:
        cursor = self._connection.cursor()
        cursor.execute("SELECT id FROM cuadrantes WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        cuadrante_id = row["id"] if row else None
        if remote:
            man_min = self._join_minutes(snapshot.get("man_h"), snapshot.get("man_m"))
            tar_min = self._join_minutes(snapshot.get("tar_h"), snapshot.get("tar_m"))
            data = {
                "delegada_uuid": snapshot.get("delegada_uuid"),
                "dia_semana": snapshot.get("dia_semana"),
                "man_min": man_min,
                "tar_min": tar_min,
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
        else:
            data = {
                "delegada_uuid": snapshot.get("delegada_uuid"),
                "dia_semana": snapshot.get("dia_semana"),
                "man_min": self._int_or_zero(snapshot.get("man_min")),
                "tar_min": self._int_or_zero(snapshot.get("tar_min")),
                "updated_at": snapshot.get("updated_at") or self._now_iso(),
                "source_device": snapshot.get("source_device"),
                "deleted": self._int_or_zero(snapshot.get("deleted")),
            }
        if mark_dirty:
            data["updated_at"] = self._now_iso()
            data["source_device"] = self._device_id_provider()
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
    def _is_local_newer(local_snapshot: dict, remote_snapshot: dict) -> bool:
        local_updated = ConflictsService._parse_iso(local_snapshot.get("updated_at"))
        remote_updated = ConflictsService._parse_iso(remote_snapshot.get("updated_at"))
        if local_updated and remote_updated:
            return local_updated >= remote_updated
        if local_updated and not remote_updated:
            return True
        if remote_updated and not local_updated:
            return False
        return True

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
        return ConflictsService._int_or_zero(hours) * 60 + ConflictsService._int_or_zero(minutes)

    @staticmethod
    def _parse_iso(value) -> datetime | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except ValueError:
            return None

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
