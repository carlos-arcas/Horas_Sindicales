from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto as SistemaArchivosBasePuerto


@dataclass(frozen=True)
class RepoInfo:
    root: Path
    branch: str | None
    commit: str | None


class RelojPuerto(Protocol):
    def ahora_utc(self) -> datetime: ...


class RepositorioInfoPuerto(Protocol):
    def obtener_info(self) -> RepoInfo: ...


class SistemaArchivosPuerto(SistemaArchivosBasePuerto, Protocol):
    def listar_python(self, base: Path) -> list[Path]: ...

    def mkdirs(self, ruta: Path) -> None: ...


class HashPuerto(Protocol):
    def sha256_texto(self, contenido: str) -> str: ...
