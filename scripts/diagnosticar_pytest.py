from __future__ import annotations

import argparse
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
PYTEST_RESULT_LOG = LOGS_DIR / "pytest_result.json"
MAX_LINEAS_RESUMEN = 200

LOGGER = logging.getLogger(__name__)


def recortar_primeras_lineas(
    texto: str, max_lineas: int = MAX_LINEAS_RESUMEN
) -> list[str]:
    return texto.splitlines()[:max_lineas]


def construir_resultado_json(
    *,
    returncode: int,
    cmd: list[str],
    stdout: str,
    stderr: str,
    max_lineas: int = MAX_LINEAS_RESUMEN,
) -> dict[str, Any]:
    return {
        "returncode": returncode,
        "cmd": cmd,
        "python": sys.version,
        "platform": platform.platform(),
        "primeras_lineas_stdout": recortar_primeras_lineas(stdout, max_lineas),
        "primeras_lineas_stderr": recortar_primeras_lineas(stderr, max_lineas),
    }


def serializar_resultado_json(resultado: dict[str, Any]) -> str:
    return json.dumps(resultado, ensure_ascii=False, indent=2)


def _escribir_archivo(ruta: Path, contenido: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")


def ejecutar_pytest(cmd: list[str], cwd: Path) -> dict[str, Any]:
    resultado = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )

    _escribir_archivo(PYTEST_STDOUT_LOG, resultado.stdout)
    _escribir_archivo(PYTEST_STDERR_LOG, resultado.stderr)

    resumen = construir_resultado_json(
        returncode=resultado.returncode,
        cmd=cmd,
        stdout=resultado.stdout,
        stderr=resultado.stderr,
    )
    _escribir_archivo(PYTEST_RESULT_LOG, serializar_resultado_json(resumen))

    LOGGER.info(
        "diagnostico_pytest_generado",
        extra={
            "returncode": resultado.returncode,
            "pytest_stdout_log": str(PYTEST_STDOUT_LOG),
            "pytest_stderr_log": str(PYTEST_STDERR_LOG),
            "pytest_result_log": str(PYTEST_RESULT_LOG),
        },
    )

    return resumen


def _parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner de diagnóstico para pytest")
    parser.add_argument(
        "--marker", default="not ui", help='Marker para pytest, p.ej. "not ui"'
    )
    parser.add_argument(
        "--extra-args",
        nargs="*",
        default=[],
        help="Argumentos extra que se añaden al comando de pytest",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    args = _parsear_args()
    comando = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        args.marker,
        *args.extra_args,
    ]

    resultado = ejecutar_pytest(cmd=comando, cwd=ROOT)
    return int(resultado["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
