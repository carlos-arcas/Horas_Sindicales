from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.application.auditoria_e2e.puertos import RepoInfo
from app.infrastructure.auditoria_e2e.adaptadores import Sha256Hasher, SistemaArchivosLocal
from tests.utilidades.normalizar_reportes import guardar_golden, normalizar_json


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2026, 2, 20, 10, 30, tzinfo=timezone.utc)


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



def test_auditoria_e2e_snapshot_manifest_json(tmp_path: Path) -> None:
    _seed(tmp_path)
    auditor = AuditarE2E(reloj=RelojFijo(), fs=SistemaArchivosLocal(), repo_info=RepoTmp(tmp_path), hasher=Sha256Hasher())

    auditor.ejecutar(RequestAuditoriaE2E(dry_run=False, id_auditoria="AUD-TEST-0003"))
    manifest_path = tmp_path / "logs" / "evidencias" / "AUD-TEST-0003" / "manifest.json"
    actual = normalizar_json(json.loads(manifest_path.read_text(encoding="utf-8")))

    golden = Path(__file__).resolve().parents[1] / "golden" / "auditoria_e2e_manifest.json"
    actual_text = json.dumps(actual, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if os.getenv("UPDATE_GOLDEN") == "1":
        guardar_golden(golden, actual_text)

    esperado = json.loads(golden.read_text(encoding="utf-8"))
    assert actual == esperado
