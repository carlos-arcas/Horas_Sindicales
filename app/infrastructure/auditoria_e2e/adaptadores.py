from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.puertos import HashPuerto, RepoInfo, RelojPuerto, RepositorioInfoPuerto, SistemaArchivosPuerto


class RelojSistema(RelojPuerto):
    def ahora_utc(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class RepoInfoGit(RepositorioInfoPuerto):
    def __init__(self, root: Path) -> None:
        self._root = root

    def obtener_info(self) -> RepoInfo:
        return RepoInfo(
            root=self._root,
            branch=self._run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            commit=self._run_git(["rev-parse", "--short", "HEAD"]),
        )

    def _run_git(self, args: list[str]) -> str | None:
        result = subprocess.run(["git", *args], cwd=self._root, capture_output=True, text=True, check=False)
        value = result.stdout.strip()
        return value or None


class SistemaArchivosLocal(SistemaArchivosPuerto):
    def existe(self, ruta: Path) -> bool:
        return ruta.exists()

    def leer_texto(self, ruta: Path) -> str:
        return ruta.read_text(encoding="utf-8")

    def listar_python(self, base: Path) -> list[Path]:
        if not base.exists():
            return []
        return sorted(base.rglob("*.py"))

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        ruta.write_text(contenido, encoding="utf-8")

    def mkdirs(self, ruta: Path) -> None:
        ruta.mkdir(parents=True, exist_ok=True)


class Sha256Hasher(HashPuerto):
    def sha256_texto(self, contenido: str) -> str:
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()
