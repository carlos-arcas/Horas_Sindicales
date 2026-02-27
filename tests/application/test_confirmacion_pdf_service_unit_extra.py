from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.use_cases.solicitudes.confirmacion_pdf_service import (
    PathFileSystem,
    actualizar_pdf_en_repo,
    generar_incident_id,
    hash_file,
    pdf_intro_text,
)
from app.application.dto import SolicitudDTO


@dataclass
class _Config:
    pdf_intro_text: str | None


class _RepoFake:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str | None]] = []

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        self.calls.append((solicitud_id, pdf_path, pdf_hash))


def _solicitud(*, solicitud_id: int | None = 7) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=1,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-01",
        desde=None,
        hasta=None,
        completo=True,
        horas=8,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_generar_incident_id_formato() -> None:
    incident = generar_incident_id()

    assert incident.startswith("INC-")
    assert len(incident) == 16


def test_pdf_intro_text_normaliza_vacios() -> None:
    assert pdf_intro_text(None) is None
    assert pdf_intro_text(_Config("   ")) is None
    assert pdf_intro_text(_Config("  Texto válido  ")) == "Texto válido"


def test_hash_file_y_path_filesystem_basico(tmp_path: Path) -> None:
    fs = PathFileSystem()
    folder = tmp_path / "out"
    file_path = folder / "doc.txt"

    fs.mkdir(folder)
    fs.escribir_texto(file_path, "hola")

    assert fs.existe(file_path)
    assert fs.leer_texto(file_path) == "hola"
    assert hash_file(file_path) == hash_file(file_path)
    assert fs.listar(folder) == [file_path]
    assert fs.listar(tmp_path / "missing") == []


def test_actualizar_pdf_en_repo_respeta_solicitud_sin_id(tmp_path: Path) -> None:
    repo = _RepoFake()
    solicitud = _solicitud(solicitud_id=None)

    actualizada = actualizar_pdf_en_repo(repo, solicitud, tmp_path / "a.pdf", "abc")

    assert actualizada is solicitud
    assert repo.calls == []


def test_actualizar_pdf_en_repo_persistiendo_info(tmp_path: Path) -> None:
    repo = _RepoFake()
    solicitud = _solicitud(solicitud_id=44)
    pdf_path = tmp_path / "b.pdf"

    actualizada = actualizar_pdf_en_repo(repo, solicitud, pdf_path, "hash-1")

    assert repo.calls == [(44, str(pdf_path), "hash-1")]
    assert actualizada.id == 44
    assert actualizada.pdf_path == str(pdf_path)
    assert actualizada.pdf_hash == "hash-1"
