from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from app.application.auditoria_e2e.caso_uso import AuditarE2E
from app.application.auditoria_e2e.dto import RequestAuditoriaE2E
from app.bootstrap.logging import configure_logging
from app.infrastructure.auditoria_e2e.adaptadores import RepoInfoGit, RelojSistema, Sha256Hasher, SistemaArchivosLocal


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auditoría E2E del proyecto")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir artefactos")
    parser.add_argument("--write", action="store_true", help="Escribe artefactos de auditoría")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dry_run and args.write:
        return 3

    dry_run = not args.write
    root = Path(__file__).resolve().parents[2]
    configure_logging(root / "logs")
    logger = logging.getLogger("app.cli_auditoria")

    auditor = AuditarE2E(
        reloj=RelojSistema(),
        fs=SistemaArchivosLocal(),
        repo_info=RepoInfoGit(root),
        hasher=Sha256Hasher(),
    )
    try:
        resultado = auditor.ejecutar(RequestAuditoriaE2E(dry_run=dry_run))
    except Exception:
        logger.exception("Error interno ejecutando auditoría E2E")
        return 3

    salida = {
        "id_auditoria": resultado.id_auditoria,
        "resultado_global": resultado.resultado_global,
        "dry_run": resultado.dry_run,
        "exit_code": resultado.exit_code,
    }
    sys.stdout.write(json.dumps(salida, ensure_ascii=False) + "\n")
    logger.info("Auditoría E2E finalizada", extra={"extra": salida})
    return resultado.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
