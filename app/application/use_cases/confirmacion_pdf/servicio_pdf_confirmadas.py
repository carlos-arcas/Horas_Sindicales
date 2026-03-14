from __future__ import annotations

import hashlib
import uuid
from dataclasses import replace
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.domain.models import GrupoConfig
from app.domain.ports import SolicitudRepository


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
    repo: SolicitudRepository,
    solicitud: SolicitudDTO,
    pdf_path: Path,
    pdf_hash: str | None,
) -> SolicitudDTO:
    if solicitud.id is None:
        return solicitud
    repo.update_pdf_info(solicitud.id, str(pdf_path), pdf_hash)
    return replace(solicitud, pdf_path=str(pdf_path), pdf_hash=pdf_hash)
