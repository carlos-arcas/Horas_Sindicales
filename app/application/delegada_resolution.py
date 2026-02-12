from __future__ import annotations

import sqlite3


def get_or_resolve_delegada_uuid(
    connection: sqlite3.Connection,
    delegada_uuid: str | None,
    delegada_nombre: str | None,
) -> str | None:
    """Devuelve un UUID de delegada válido para la BD local.

    - Si delegada_uuid existe en local, lo usa.
    - Si no, intenta por delegada_nombre (normalizando espacios y casefold).
    - Si no hay coincidencia exacta por nombre, devuelve None (no crea registros).
    """

    uuid_value = str(delegada_uuid or "").strip()
    nombre_value = " ".join(str(delegada_nombre or "").split())
    cursor = connection.cursor()

    if uuid_value:
        cursor.execute("SELECT uuid FROM personas WHERE uuid = ?", (uuid_value,))
        row = cursor.fetchone()
        if row:
            return str(row["uuid"])

    if not nombre_value:
        return None

    normalized_target = nombre_value.casefold()

    cursor.execute("SELECT uuid, nombre FROM personas")
    for row in cursor.fetchall():
        nombre_persona = " ".join(str(row["nombre"] or "").split()).casefold()
        uuid_persona = str(row["uuid"] or "").strip()
        if nombre_persona == normalized_target and uuid_persona:
            return uuid_persona

    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'delegadas'")
    if cursor.fetchone() is None:
        return None
    cursor.execute("SELECT uuid, nombre FROM delegadas")
    for row in cursor.fetchall():
        nombre_delegada = " ".join(str(row["nombre"] or "").split()).casefold()
        uuid_delegada = str(row["uuid"] or "").strip()
        if nombre_delegada == normalized_target and uuid_delegada:
            return uuid_delegada
    return None
