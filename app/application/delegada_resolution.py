from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_or_resolve_delegada_uuid(
    connection: sqlite3.Connection,
    delegada_uuid: str | None,
    delegada_nombre: str | None,
) -> str | None:
    """Devuelve un UUID de delegada válido para la BD local.

    - Si delegada_uuid existe en local, lo usa.
    - Si no, intenta por delegada_nombre.
    - Si no existe por nombre y hay nombre, crea una delegada mínima local y devuelve su uuid.
    - Si no hay uuid ni nombre utilizables, devuelve None.
    """

    uuid_value = str(delegada_uuid or "").strip()
    nombre_value = str(delegada_nombre or "").strip()
    cursor = connection.cursor()

    if uuid_value:
        cursor.execute("SELECT uuid FROM personas WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        if row:
            return str(row["uuid"])

    if not nombre_value:
        return None

    cursor.execute("SELECT uuid FROM personas WHERE nombre = ?", (nombre_value,))
    by_name = cursor.fetchone()
    if by_name and str(by_name["uuid"] or "").strip():
        return str(by_name["uuid"]).strip()

    generated_uuid = uuid_value or str(uuid.uuid4())
    now_iso = _now_iso()
    cursor.execute(
        """
        INSERT INTO personas (
            uuid, nombre, genero, horas_mes_min, horas_ano_min,
            cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
            cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
            cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
            cuad_dom_man_min, cuad_dom_tar_min, updated_at, source_device, deleted, is_active
        ) VALUES (?, ?, 'F', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?, 'sync_sheets_pull', 0, 1)
        """,
        (generated_uuid, nombre_value, now_iso),
    )
    connection.commit()
    return generated_uuid
