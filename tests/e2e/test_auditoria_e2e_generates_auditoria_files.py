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


def _seed(root: Path) -> None:
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


def test_auditoria_e2e_write_genera_reportes_canonicos(tmp_path: Path) -> None:
    _seed(tmp_path)
    auditor = AuditarE2E(reloj=RelojSistema(), fs=SistemaArchivosLocal(), repo_info=RepoTmp(tmp_path), hasher=Sha256Hasher())

    resultado = auditor.ejecutar(RequestAuditoriaE2E(dry_run=False, id_auditoria="AUD-TEST-0002"))

    base = tmp_path / "logs" / "evidencias" / "AUD-TEST-0002"
    assert resultado.artefactos_generados
    assert (base / "AUDITORIA.md").exists()
    assert (base / "auditoria.json").exists()
    assert (base / "manifest.json").exists()
    assert (base / "status.txt").exists()

    payload = json.loads((base / "auditoria.json").read_text(encoding="utf-8"))
    assert payload["metadatos"]["id_auditoria"] == "AUD-TEST-0002"
    assert payload["resultado_global"] in {"PASS", "FAIL"}
    assert "scorecard" in payload
    assert isinstance(payload["checks"], list)

    markdown = (base / "AUDITORIA.md").read_text(encoding="utf-8")
    assert "Resultado global" in markdown
    assert "Backlog recomendado" in markdown
