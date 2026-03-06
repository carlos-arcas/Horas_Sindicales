from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys

LOGGER = logging.getLogger(__name__)


def _mypy_disponible() -> bool:
    return importlib.util.find_spec("mypy") is not None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not _mypy_disponible():
        LOGGER.error("ERROR: falta mypy en requirements-dev.txt")
        return 1

    comando = [
        sys.executable,
        "-m",
        "mypy",
        "--config-file",
        ".config/mypy.ini",
    ]
    resultado = subprocess.run(comando, check=False)
    return resultado.returncode


if __name__ == "__main__":
    raise SystemExit(main())
