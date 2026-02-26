from __future__ import annotations

import uuid
from pathlib import Path

from app.application.dtos.contexto_operacion import ContextoOperacion
from app.domain.models import GrupoConfig


def _generar_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:12].upper()}"


class _PathFileSystem:
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


def _resolver_correlation_id(
    correlation_id: str | None,
    contexto: ContextoOperacion | None,
) -> str | None:
    if contexto is not None:
        return contexto.correlation_id
    return correlation_id

MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}



def pdf_intro_text(config: GrupoConfig | None) -> str | None:
    if config is None:
        return None
    intro = (config.pdf_intro_text or "").strip()
    return intro or None
