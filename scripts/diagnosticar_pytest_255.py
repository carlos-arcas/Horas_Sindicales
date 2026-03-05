from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
PYTEST_STDOUT_LOG = LOGS_DIR / "pytest_stdout.log"
PYTEST_STDERR_LOG = LOGS_DIR / "pytest_stderr.log"
PYTEST_FAILURE_SUMMARY = LOGS_DIR / "pytest_failure_summary.json"
PYTEST_COMMAND = [sys.executable, "-m", "pytest", "-q", "-m", "not ui"]

LOGGER = logging.getLogger(__name__)


def recortar_primeras_lineas(texto: str, max_lineas: int = 200) -> list[str]:
    return texto.splitlines()[:max_lineas]


def construir_resumen_fallo(returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
    return {
        "returncode": returncode,
        "first_200_lines_stdout": recortar_primeras_lineas(stdout, max_lineas=200),
        "first_200_lines_stderr": recortar_primeras_lineas(stderr, max_lineas=200),
        "platform": platform.platform(),
        "python_version": sys.version,
    }


def serializar_resumen_json(resumen: dict[str, Any]) -> str:
    return json.dumps(resumen, ensure_ascii=False, indent=2)


def _escribir_archivo(ruta: Path, contenido: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    resultado = subprocess.run(
        PYTEST_COMMAND,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    _escribir_archivo(PYTEST_STDOUT_LOG, resultado.stdout)
    _escribir_archivo(PYTEST_STDERR_LOG, resultado.stderr)

    LOGGER.info(
        "diagnostico_pytest_ejecutado",
        extra={
            "returncode": resultado.returncode,
            "comando": PYTEST_COMMAND,
            "stdout_log": str(PYTEST_STDOUT_LOG),
            "stderr_log": str(PYTEST_STDERR_LOG),
        },
    )

    if resultado.returncode != 0:
        resumen_fallo = construir_resumen_fallo(
            returncode=resultado.returncode,
            stdout=resultado.stdout,
            stderr=resultado.stderr,
        )
        _escribir_archivo(
            PYTEST_FAILURE_SUMMARY,
            serializar_resumen_json(resumen_fallo),
        )
        LOGGER.error(
            "diagnostico_pytest_fallo",
            extra={
                "returncode": resultado.returncode,
                "summary_log": str(PYTEST_FAILURE_SUMMARY),
            },
        )

    return resultado.returncode


if __name__ == "__main__":
    raise SystemExit(main())
