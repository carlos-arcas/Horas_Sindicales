from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CargadorComunidadDemoSQLite:
    def __init__(self, connection: sqlite3.Connection, dataset: dict[str, object]) -> None:
        self._connection = connection
        self._dataset = dataset

    def cargar(self) -> tuple[int, int]:
        perfiles = self._dataset.get("perfiles", [])
        publicaciones = self._dataset.get("publicaciones", [])
        if not isinstance(perfiles, list) or not isinstance(publicaciones, list):
            raise ValueError("dataset_comunidad_invalido")

        total_perfiles = 0
        total_publicaciones = 0
        for perfil in perfiles:
            self._upsert_perfil(perfil)
            total_perfiles += 1
        for publicacion in publicaciones:
            self._upsert_publicacion(publicacion)
            total_publicaciones += 1
        self._connection.commit()
        logger.info(
            "carga_demo_comunidad_completada",
            extra={"perfiles": total_perfiles, "publicaciones": total_publicaciones},
        )
        return total_perfiles, total_publicaciones

    def _upsert_perfil(self, perfil: dict[str, object]) -> None:
        ahora = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            INSERT INTO comunidad_perfiles (perfil_id, alias, bio, disciplina_principal, seguidores, activo, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(perfil_id) DO UPDATE SET
                alias=excluded.alias,
                bio=excluded.bio,
                disciplina_principal=excluded.disciplina_principal,
                seguidores=excluded.seguidores,
                activo=excluded.activo,
                actualizado_en=excluded.actualizado_en
            """,
            (
                str(perfil["perfil_id"]),
                str(perfil["alias"]),
                str(perfil.get("bio", "")),
                str(perfil["disciplina_principal"]),
                int(perfil.get("seguidores", 0)),
                1,
                ahora,
            ),
        )

    def _upsert_publicacion(self, publicacion: dict[str, object]) -> None:
        self._connection.execute(
            """
            INSERT INTO comunidad_publicaciones (
                publicacion_id, perfil_id, disciplina, titulo, resumen, likes, comentarios, publicado_en, activa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(publicacion_id) DO UPDATE SET
                perfil_id=excluded.perfil_id,
                disciplina=excluded.disciplina,
                titulo=excluded.titulo,
                resumen=excluded.resumen,
                likes=excluded.likes,
                comentarios=excluded.comentarios,
                publicado_en=excluded.publicado_en,
                activa=excluded.activa
            """,
            (
                str(publicacion["publicacion_id"]),
                str(publicacion["perfil_id"]),
                str(publicacion["disciplina"]),
                str(publicacion["titulo"]),
                str(publicacion.get("resumen", "")),
                int(publicacion.get("likes", 0)),
                int(publicacion.get("comentarios", 0)),
                str(publicacion["publicado_en"]),
                1,
            ),
        )
