from __future__ import annotations

from pathlib import Path

from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto


class SistemaArchivosLocal(SistemaArchivosPuerto):
    def existe(self, ruta: Path) -> bool:
        return ruta.exists()

    def leer_texto(self, ruta: Path) -> str:
        return ruta.read_text(encoding="utf-8")

    def leer_bytes(self, ruta: Path) -> bytes:
        return ruta.read_bytes()

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        ruta.write_text(contenido, encoding="utf-8")

    def escribir_bytes(self, ruta: Path, contenido: bytes) -> None:
        ruta.write_bytes(contenido)

    def mkdir(self, ruta: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        ruta.mkdir(parents=parents, exist_ok=exist_ok)

    def listar(self, base: Path) -> list[Path]:
        if not base.exists():
            return []
        return sorted(base.iterdir())

    def listar_python(self, base: Path) -> list[Path]:
        if not base.exists():
            return []
        return sorted(base.rglob("*.py"))

    def mkdirs(self, ruta: Path) -> None:
        self.mkdir(ruta, parents=True, exist_ok=True)
