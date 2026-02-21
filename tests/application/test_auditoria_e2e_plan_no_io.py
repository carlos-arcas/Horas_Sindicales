from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.application.auditoria_e2e.puertos import RepoInfo


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2026, 2, 20, 10, 30, 0, tzinfo=timezone.utc)


class HashFijo:
    def sha256_texto(self, contenido: str) -> str:
        return "abc12345" * 8


class RepoFijo:
    def __init__(self, root: Path) -> None:
        self.root = root

    def obtener_info(self) -> RepoInfo:
        return RepoInfo(root=self.root, branch="main", commit="deadbee")


class FSSinIO:
    def __init__(self) -> None:
        self.writes = 0

    def existe(self, ruta: Path) -> bool:
        return False

    def leer_texto(self, ruta: Path) -> str:
        return ""

    def listar_python(self, base: Path) -> list[Path]:
        return []

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        self.writes += 1

    def mkdirs(self, ruta: Path) -> None:
        self.writes += 1


def test_plan_rutas_conflictos_sin_io() -> None:
    fs = FSSinIO()
    auditor = AuditarE2E(reloj=RelojFijo(), fs=fs, repo_info=RepoFijo(Path("/repo")), hasher=HashFijo())

    plan = auditor.obtener_plan(RequestAuditoriaE2E(dry_run=True))
    rutas = auditor.obtener_rutas(plan)
    conflictos = auditor.validar_conflictos(plan)

    assert plan.id_auditoria == "AUD-20260220-103000-abc12345"
    assert rutas.base_dir.endswith(plan.id_auditoria)
    assert conflictos.conflictos == []
    assert fs.writes == 0
