from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.testing.qt_harness import (
    _construir_args_pytest_core_no_ui,
    _construir_env_pytest_core_no_ui,
)

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
PYTEST_STDOUT_LOG = LOGS_DIR / "pytest_stdout.log"
PYTEST_STDERR_LOG = LOGS_DIR / "pytest_stderr.log"
PYTEST_RESULT_LOG = LOGS_DIR / "pytest_result.json"
PYTEST_STDOUT_255_VV_LOG = LOGS_DIR / "pytest_stdout_255_vv.log"
PYTEST_STDERR_255_VV_LOG = LOGS_DIR / "pytest_stderr_255_vv.log"
PYTEST_RESULT_255_VV_LOG = LOGS_DIR / "pytest_result_255_vv.json"
MAX_LINEAS_HEAD = 200
MAX_LINEAS_TAIL = 200

LOGGER = logging.getLogger(__name__)
RE_TEST_VV = re.compile(r"^(tests/.+::test[^\s]*)")


def recortar_head_tail(texto: str, head: int, tail: int) -> dict[str, list[str]]:
    lineas = texto.splitlines()
    return {
        "head": lineas[: max(head, 0)],
        "tail": lineas[-max(tail, 0) :] if tail > 0 else [],
    }


def calcular_returncode_hex(returncode: int) -> str:
    if platform.system().lower().startswith("win"):
        return f"0x{returncode & 0xFFFFFFFF:08X}"
    return hex(returncode)


def detectar_ultimo_test_visto(lineas: list[str]) -> str | None:
    ultimo_test: str | None = None
    for linea in lineas:
        coincidencia = RE_TEST_VV.match(linea.strip())
        if coincidencia:
            ultimo_test = coincidencia.group(1)
    return ultimo_test


def construir_resultado_json(
    *,
    returncode: int,
    cmd: list[str],
    stdout: str,
    stderr: str,
    head: int = MAX_LINEAS_HEAD,
    tail: int = MAX_LINEAS_TAIL,
) -> dict[str, Any]:
    stdout_recortado = recortar_head_tail(stdout, head, tail)
    stderr_recortado = recortar_head_tail(stderr, head, tail)
    return {
        "returncode": returncode,
        "returncode_hex": calcular_returncode_hex(returncode),
        "cmd": cmd,
        "python": sys.version,
        "platform": platform.platform(),
        "stdout_head": stdout_recortado["head"],
        "stdout_tail": stdout_recortado["tail"],
        "stderr_head": stderr_recortado["head"],
        "stderr_tail": stderr_recortado["tail"],
    }


def serializar_resultado_json(resultado: dict[str, Any]) -> str:
    return json.dumps(resultado, ensure_ascii=False, indent=2)


def _escribir_archivo(ruta: Path, contenido: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")


def _ejecutar_subproceso(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    entorno = {**os.environ, "PYTHONFAULTHANDLER": "1", "PYTHONUNBUFFERED": "1"}
    if env is not None:
        entorno.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )


def ejecutar_pytest(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    resultado = _ejecutar_subproceso(cmd=cmd, cwd=cwd, env=env)

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


def ejecutar_rerun_verbose(
    marker: str,
    cwd: Path,
    core_no_ui: bool = False,
) -> dict[str, Any]:
    args_pytest = ["-m", marker, "-vv", "-x"]
    env_extra: dict[str, str] | None = None
    if core_no_ui:
        args_pytest = _construir_args_pytest_core_no_ui(args_pytest)
        env_extra = _construir_env_pytest_core_no_ui()
    comando_rerun = [
        sys.executable,
        "-X",
        "faulthandler",
        "-m",
        "pytest",
        *args_pytest,
    ]
    resultado = _ejecutar_subproceso(cmd=comando_rerun, cwd=cwd, env=env_extra)
    _escribir_archivo(PYTEST_STDOUT_255_VV_LOG, resultado.stdout)
    _escribir_archivo(PYTEST_STDERR_255_VV_LOG, resultado.stderr)

    resumen_rerun = construir_resultado_json(
        returncode=resultado.returncode,
        cmd=comando_rerun,
        stdout=resultado.stdout,
        stderr=resultado.stderr,
    )
    resumen_rerun["last_test_seen"] = detectar_ultimo_test_visto(
        resumen_rerun["stdout_tail"]
    )
    _escribir_archivo(
        PYTEST_RESULT_255_VV_LOG, serializar_resultado_json(resumen_rerun)
    )

    LOGGER.info(
        "diagnostico_pytest_rerun_255_generado",
        extra={
            "returncode": resultado.returncode,
            "pytest_stdout_log": str(PYTEST_STDOUT_255_VV_LOG),
            "pytest_stderr_log": str(PYTEST_STDERR_255_VV_LOG),
            "pytest_result_log": str(PYTEST_RESULT_255_VV_LOG),
            "last_test_seen": resumen_rerun["last_test_seen"],
        },
    )

    return resumen_rerun


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
    parser.add_argument(
        "--rerun-verbose-on-255",
        default="true",
        choices=["true", "false"],
        help="Si está en true, relanza pytest en -vv -x cuando returncode sea 255",
    )
    parser.add_argument(
        "--core-no-ui",
        default="false",
        choices=["true", "false"],
        help="Activa política core/no-ui: bloquea autoload global y desactiva pytest-qt.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    args = _parsear_args()
    args_pytest = ["-q", "-m", args.marker, *args.extra_args]
    core_no_ui = args.core_no_ui.lower() == "true"
    env_extra: dict[str, str] | None = None
    if core_no_ui:
        args_pytest = _construir_args_pytest_core_no_ui(args_pytest)
        env_extra = _construir_env_pytest_core_no_ui()

    comando = [
        sys.executable,
        "-X",
        "faulthandler",
        "-m",
        "pytest",
        *args_pytest,
    ]

    resultado = ejecutar_pytest(cmd=comando, cwd=ROOT, env=env_extra)
    rerun_habilitado = args.rerun_verbose_on_255.lower() == "true"
    if rerun_habilitado and int(resultado["returncode"]) == 255:
        ejecutar_rerun_verbose(args.marker, ROOT, core_no_ui=core_no_ui)

    return int(resultado["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
