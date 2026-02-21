from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.puertos import RepoInfo
from app.application.dto import SolicitudDTO
from app.application.operaciones.auditoria_e2e_operacion import OperacionAuditoriaE2E, RequestOperacionAuditoria
from app.application.operaciones.exportacion_pdf_historico_operacion import (
    ExportacionPdfHistoricoOperacion,
    RequestExportacionPdfHistorico,
)
from app.domain.models import Persona
from app.infrastructure.auditoria_e2e.adaptadores import Sha256Hasher
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2026, 2, 20, 10, 30, 0, tzinfo=timezone.utc)


class RepoTmp:
    def __init__(self, root: Path) -> None:
        self._root = root

    def obtener_info(self) -> RepoInfo:
        return RepoInfo(root=self._root, branch="test", commit="abc")


class GeneradorPdfSpy:
    def __init__(self) -> None:
        self.called = False

    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: list[str]) -> str:
        _ = (nombre_solicitante, fechas)
        return "historico.pdf"

    def generar_pdf_solicitudes(self, solicitudes, persona, destino, intro_text=None, logo_path=None, include_hours_in_horario=None):
        raise AssertionError("No aplica")

    def generar_pdf_historico(self, solicitudes, persona, destino, intro_text=None, logo_path=None):
        self.called = True
        destino.write_bytes(b"%PDF-1.4 fake")
        return destino


def _crear_repo_minimo(root: Path) -> None:
    (root / "app" / "bootstrap").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "requirements.txt").write_text("pytest==8.3.0\n", encoding="utf-8")
    (root / "requirements-dev.txt").write_text("pytest==8.3.0\n", encoding="utf-8")
    (root / "lanzar_app.bat").write_text("@echo off\n", encoding="utf-8")
    (root / "ejecutar_tests.bat").write_text("pytest --cov=.\n", encoding="utf-8")
    (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## [1.0.0] - 2026-02-20\n- ok\n", encoding="utf-8")
    (root / "app" / "bootstrap" / "logging.py").write_text("RotatingFileHandler\ncrashes.log\n", encoding="utf-8")
    for doc in ["arquitectura.md", "decisiones_tecnicas.md", "guia_pruebas.md", "guia_logging.md", "definicion_producto_final.md"]:
        (root / "docs" / doc).write_text("# doc\ncontenido\n", encoding="utf-8")


def _persona() -> Persona:
    return Persona(1, "Delegada", "F", 600, 7200, True, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 0, 0, 0, 0)


def _solicitud() -> SolicitudDTO:
    return SolicitudDTO(1, 1, "2025-01-10", "2025-01-15", "09:00", "11:00", False, 2.0, "Obs", None, None)


def test_operaciones_dry_run_no_escriben(tmp_path: Path) -> None:
    fs = SistemaArchivosLocal()

    repo_root = tmp_path / "repo"
    _crear_repo_minimo(repo_root)
    auditor = AuditarE2E(reloj=RelojFijo(), fs=fs, repo_info=RepoTmp(repo_root), hasher=Sha256Hasher())
    op_auditoria = OperacionAuditoriaE2E(auditor)
    resultado_auditoria = op_auditoria.ejecutar(RequestOperacionAuditoria(dry_run=True, id_auditoria="AUD-DRY-1"))

    pdf_destino = tmp_path / "salidas" / "historico.pdf"
    generador = GeneradorPdfSpy()
    op_pdf = ExportacionPdfHistoricoOperacion(fs=fs, generador_pdf=generador)
    resultado_pdf = op_pdf.ejecutar(
        RequestExportacionPdfHistorico(
            solicitudes=[_solicitud()],
            persona=_persona(),
            destino=pdf_destino,
            dry_run=True,
        )
    )

    assert resultado_auditoria.artefactos_generados == []
    assert resultado_pdf.artefactos_generados == []
    assert not (repo_root / "logs" / "evidencias" / "AUD-DRY-1").exists()
    assert not pdf_destino.exists()
    assert generador.called is False
