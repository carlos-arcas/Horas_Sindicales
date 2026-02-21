from __future__ import annotations

from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.application.auditoria_e2e.puertos import RepoInfo
from app.infrastructure.auditoria_e2e.adaptadores import RelojSistema, Sha256Hasher, SistemaArchivosLocal


class RepoTmp:
    def __init__(self, root: Path) -> None:
        self._root = root

    def obtener_info(self) -> RepoInfo:
        return RepoInfo(root=self._root, branch="test", commit="abc")


class SpyFS(SistemaArchivosLocal):
    def __init__(self) -> None:
        self.writes: list[Path] = []

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        self.writes.append(ruta)
        super().escribir_texto(ruta, contenido)

    def mkdirs(self, ruta: Path) -> None:
        self.writes.append(ruta)
        super().mkdirs(ruta)


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


def test_dry_run_no_escribe_en_disco(tmp_path: Path) -> None:
    _crear_repo_minimo(tmp_path)
    fs = SpyFS()
    auditor = AuditarE2E(reloj=RelojSistema(), fs=fs, repo_info=RepoTmp(tmp_path), hasher=Sha256Hasher())

    resultado = auditor.ejecutar(RequestAuditoriaE2E(dry_run=True, id_auditoria="AUD-TEST-0001"))

    assert resultado.dry_run is True
    assert resultado.artefactos_generados == []
    assert fs.writes == []
    assert not (tmp_path / "logs" / "evidencias" / "AUD-TEST-0001").exists()
