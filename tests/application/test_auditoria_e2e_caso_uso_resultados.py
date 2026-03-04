from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import (
    CheckAuditoria,
    EstadoCheck,
    RequestAuditoriaE2E,
    SeveridadCheck,
)
from app.application.auditoria_e2e.puertos import RepoInfo


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)


class HashDeterminista:
    def sha256_texto(self, contenido: str) -> str:
        return f"hash-{len(contenido)}"


class RepoFijo:
    def __init__(self, root: Path) -> None:
        self._info = RepoInfo(root=root, branch="main", commit="c0ffee42")

    def obtener_info(self) -> RepoInfo:
        return self._info


class FSEnMemoria:
    def __init__(self) -> None:
        self.archivos: dict[Path, str] = {}
        self.directorios: set[Path] = set()

    def existe(self, ruta: Path) -> bool:
        return ruta in self.archivos or ruta in self.directorios

    def leer_texto(self, ruta: Path) -> str:
        return self.archivos[ruta]

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        self.archivos[ruta] = contenido

    def mkdirs(self, ruta: Path) -> None:
        self.directorios.add(ruta)

    def listar_python(self, base: Path) -> list[Path]:
        return []


def _build_auditor() -> tuple[AuditarE2E, FSEnMemoria]:
    fs = FSEnMemoria()
    auditor = AuditarE2E(
        reloj=RelojFijo(),
        fs=fs,
        repo_info=RepoFijo(Path("/repo")),
        hasher=HashDeterminista(),
    )
    return auditor, fs


def test_ejecutar_dry_run_fail_no_genera_archivos(monkeypatch) -> None:
    auditor, fs = _build_auditor()
    checks = [
        CheckAuditoria("CHECK-1", EstadoCheck.PASS, SeveridadCheck.BAJO, ["ok"], "n/a"),
        CheckAuditoria("CHECK-2", EstadoCheck.NO_EVALUABLE, SeveridadCheck.MEDIO, ["pendiente"], "medir"),
        CheckAuditoria("CHECK-3", EstadoCheck.FAIL, SeveridadCheck.ALTO, ["rompe"], "arreglar"),
    ]
    monkeypatch.setattr(auditor, "_ejecutar_checks", lambda: checks)

    resultado = auditor.ejecutar(RequestAuditoriaE2E(dry_run=True, id_auditoria="AUD-X"))

    assert resultado.resultado_global == "FAIL"
    assert resultado.exit_code == 2
    assert resultado.score == 5.0
    assert resultado.artefactos_generados == []
    assert fs.archivos == {}


def test_ejecutar_no_dry_run_pass_genera_manifest_y_payload() -> None:
    auditor, fs = _build_auditor()
    checks = [
        CheckAuditoria("CHECK-1", EstadoCheck.PASS, SeveridadCheck.BAJO, ["ok"], "mantener"),
        CheckAuditoria("CHECK-2", EstadoCheck.PASS, SeveridadCheck.MEDIO, ["ok"], "mantener"),
    ]
    auditor._ejecutar_checks = lambda: checks  # type: ignore[method-assign]

    resultado = auditor.ejecutar(RequestAuditoriaE2E(dry_run=False, id_auditoria="AUD-OK"))

    assert resultado.resultado_global == "PASS"
    assert resultado.exit_code == 0
    assert resultado.score == 10.0
    assert len(resultado.artefactos_generados) == 4

    path_json = Path(resultado.rutas_previstas.auditoria_json)
    payload = json.loads(fs.archivos[path_json])
    assert payload["resultado_global"] == "PASS"
    assert payload["metadatos"]["id_auditoria"] == "AUD-OK"

    manifest = json.loads(fs.archivos[Path(resultado.rutas_previstas.manifest_json)])
    archivos = [item["archivo"] for item in manifest["archivos"]]
    assert archivos == ["AUDITORIA.md", "auditoria.json", "status.txt"]
