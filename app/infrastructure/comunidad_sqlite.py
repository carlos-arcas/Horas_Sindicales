from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain.comunidad_descubrimiento import FiltroDescubrimiento, PerfilSugerido, PublicacionDescubrimiento


class RepositorioComunidadSQLite:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def listar_publicaciones(self, filtro: FiltroDescubrimiento) -> list[PublicacionDescubrimiento]:
        where: list[str] = ["p.activa = 1"]
        params: list[object] = []
        if filtro.disciplina:
            where.append("p.disciplina = ?")
            params.append(filtro.disciplina)
        if filtro.busqueda:
            where.append("(LOWER(p.titulo) LIKE ? OR LOWER(p.resumen) LIKE ?)")
            criterio = f"%{filtro.busqueda.lower()}%"
            params.extend([criterio, criterio])

        if filtro.orden == "populares":
            order_sql = "p.likes DESC, p.comentarios DESC, p.publicado_en DESC"
        elif filtro.orden == "siguiendo":
            order_sql = "p.publicado_en DESC"
        else:
            order_sql = "p.publicado_en DESC"

        sql = f"""
            SELECT p.publicacion_id, p.perfil_id, c.alias, p.disciplina, p.titulo, p.resumen,
                   p.likes, p.comentarios, p.publicado_en
            FROM comunidad_publicaciones p
            JOIN comunidad_perfiles c ON c.perfil_id = p.perfil_id
            WHERE {' AND '.join(where)}
            ORDER BY {order_sql}
            LIMIT ?
        """
        params.append(filtro.limit)
        rows = self._connection.execute(sql, tuple(params)).fetchall()
        return [
            PublicacionDescubrimiento(
                publicacion_id=str(row["publicacion_id"]),
                perfil_id=str(row["perfil_id"]),
                alias_perfil=str(row["alias"]),
                disciplina=str(row["disciplina"]),
                titulo=str(row["titulo"]),
                resumen=str(row["resumen"]),
                likes=int(row["likes"]),
                comentarios=int(row["comentarios"]),
                publicado_en=datetime.fromisoformat(str(row["publicado_en"])),
            )
            for row in rows
        ]

    def listar_disciplinas_disponibles(self) -> list[str]:
        rows = self._connection.execute(
            """
            SELECT disciplina, COUNT(1) AS total
            FROM comunidad_publicaciones
            WHERE activa = 1
            GROUP BY disciplina
            ORDER BY total DESC, disciplina ASC
            """
        ).fetchall()
        return [str(row["disciplina"]) for row in rows]

    def listar_perfiles_sugeridos(self, limite: int = 5) -> list[PerfilSugerido]:
        rows = self._connection.execute(
            """
            SELECT perfil_id, alias, disciplina_principal, seguidores
            FROM comunidad_perfiles
            WHERE activo = 1
            ORDER BY seguidores DESC, alias ASC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [
            PerfilSugerido(
                perfil_id=str(row["perfil_id"]),
                alias=str(row["alias"]),
                disciplina_principal=str(row["disciplina_principal"]),
                seguidores=int(row["seguidores"]),
            )
            for row in rows
        ]
