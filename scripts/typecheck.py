#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MYPY_CONFIG_PATH = ROOT / ".config" / "mypy.ini"


def construir_comando() -> list[str]:
    return [sys.executable, "-m", "mypy", "--config-file", str(MYPY_CONFIG_PATH)]


def ejecutar_typecheck() -> dict[str, Any]:
    comando = construir_comando()
    resultado = subprocess.run(
        comando,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    salida = "\n".join(
        parte.strip()
        for parte in (resultado.stdout, resultado.stderr)
        if parte and parte.strip()
    )
    if resultado.returncode == 0:
        return {
            "status": "PASS",
            "errores": [],
            "comando": " ".join(comando),
            "salida": salida,
            "exit_code": 0,
        }

    errores = [linea for linea in salida.splitlines() if linea.strip()] if salida else []
    return {
        "status": "FAIL",
        "errores": errores,
        "comando": " ".join(comando),
        "salida": salida,
        "exit_code": resultado.returncode,
    }


def main() -> int:
    resultado = ejecutar_typecheck()
    print(f"typecheck={resultado['status']}")
    if resultado["salida"]:
        print(resultado["salida"])
    return 0 if resultado["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
