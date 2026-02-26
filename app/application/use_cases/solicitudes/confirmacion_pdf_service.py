from __future__ import annotations

import hashlib
import uuid
from dataclasses import replace
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.domain.models import GrupoConfig
from app.domain.ports import SolicitudRepository


class PathFileSystem(SistemaArchivosPuerto):
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


def generar_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:12].upper()}"


def pdf_intro_text(config: GrupoConfig | None) -> str | None:
    if config is None:
        return None
    intro = (config.pdf_intro_text or "").strip()
    return intro or None


def hash_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def actualizar_pdf_en_repo(
    repo: SolicitudRepository, solicitud: SolicitudDTO, pdf_path: Path, pdf_hash: str | None
) -> SolicitudDTO:
    if solicitud.id is None:
        return solicitud
    repo.update_pdf_info(solicitud.id, str(pdf_path), pdf_hash)
    return replace(solicitud, pdf_path=str(pdf_path), pdf_hash=pdf_hash)
