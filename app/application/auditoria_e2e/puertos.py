from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class RepoInfo:
    root: Path
    branch: str | None
    commit: str | None


class RelojPuerto(Protocol):
    def ahora_utc(self) -> datetime: ...


class RepositorioInfoPuerto(Protocol):
    def obtener_info(self) -> RepoInfo: ...


class SistemaArchivosPuerto(Protocol):
    def existe(self, ruta: Path) -> bool: ...

    def leer_texto(self, ruta: Path) -> str: ...

    def listar_python(self, base: Path) -> list[Path]: ...

    def escribir_texto(self, ruta: Path, contenido: str) -> None: ...

    def mkdirs(self, ruta: Path) -> None: ...


class HashPuerto(Protocol):
    def sha256_texto(self, contenido: str) -> str: ...
