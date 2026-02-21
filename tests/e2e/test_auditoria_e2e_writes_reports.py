from __future__ import annotations

import json
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.application.auditoria_e2e.puertos import RepoInfo
from app.infrastructure.auditoria_e2e.adaptadores import RelojSistema, Sha256Hasher, SistemaArchivosLocal


class RepoTmp:
    def __init__(self, root: Path) -> None:
        self._root = root

    def obtener_info(self) -> RepoInfo:
        return RepoInfo(root=self._root, branch="main", commit="abc1234")


def test_write_generates_reports(tmp_path: Path) -> None:
    (tmp_path / "app" / "bootstrap").mkdir(parents=True)
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "requirements.txt").write_text("pytest==8.3.0\n", encoding="utf-8")
    (tmp_path / "requirements-dev.txt").write_text("pytest==8.3.0\n", encoding="utf-8")
    (tmp_path / "lanzar_app.bat").write_text("@echo off\n", encoding="utf-8")
    (tmp_path / "ejecutar_tests.bat").write_text("pytest --cov=.\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## [1.0.0] - 2026-02-20\n- ok\n", encoding="utf-8")
    (tmp_path / "app" / "bootstrap" / "logging.py").write_text("RotatingFileHandler\ncrashes.log\n", encoding="utf-8")
    for doc in ["arquitectura.md", "decisiones_tecnicas.md", "guia_pruebas.md", "guia_logging.md", "definicion_producto_final.md"]:
        (tmp_path / "docs" / doc).write_text("# doc\ncontenido\n", encoding="utf-8")

    auditor = AuditarE2E(reloj=RelojSistema(), fs=SistemaArchivosLocal(), repo_info=RepoTmp(tmp_path), hasher=Sha256Hasher())
    auditor.ejecutar(RequestAuditoriaE2E(dry_run=False, id_auditoria="AUD-TEST-0002"))

    base = tmp_path / "logs" / "evidencias" / "AUD-TEST-0002"
    assert (base / "AUDITORIA.md").exists()
    payload = json.loads((base / "auditoria.json").read_text(encoding="utf-8"))
    assert payload["metadatos"]["id_auditoria"] == "AUD-TEST-0002"
