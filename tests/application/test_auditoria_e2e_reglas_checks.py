from __future__ import annotations

from pathlib import Path

from app.application.auditoria_e2e.dto import EstadoCheck
from app.application.auditoria_e2e.reglas import (
    _requirements_pinneados,
    evaluar_check_docs,
    evaluar_check_logging,
    evaluar_check_tests,
    evaluar_check_versionado,
    evaluar_check_windows_repro,
)


class FSEnMemoria:
    def __init__(self, archivos: dict[str, str]) -> None:
        self._archivos = {Path(ruta): contenido for ruta, contenido in archivos.items()}

    def existe(self, ruta: Path) -> bool:
        return ruta in self._archivos

    def leer_texto(self, ruta: Path) -> str:
        return self._archivos[ruta]

    def listar_python(self, base: Path) -> list[Path]:
        prefijo = str(base)
        return sorted(path for path in self._archivos if str(path).startswith(prefijo) and path.suffix == ".py")


def test_evaluar_check_tests_devuelve_no_evaluable_con_precondiciones() -> None:
    fs = FSEnMemoria(
        {
            "/repo/requirements-dev.txt": "pytest==8.3.2",
            "/repo/ejecutar_tests.bat": "pytest --cov=app",
        }
    )

    resultado = evaluar_check_tests(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.NO_EVALUABLE


def test_evaluar_check_tests_falla_si_falta_comando_estandar() -> None:
    fs = FSEnMemoria({"/repo/requirements-dev.txt": "pytest==8.3.2"})

    resultado = evaluar_check_tests(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.FAIL


def test_evaluar_check_logging_detecta_print_y_falta_rotacion() -> None:
    fs = FSEnMemoria(
        {
            "/repo/main.py": "print('debug')",
            "/repo/app/bootstrap/logging.py": "import logging",
        }
    )

    resultado = evaluar_check_logging(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.FAIL
    assert "Sin print en app/main=no" in resultado.evidencia[0]


def test_evaluar_check_logging_pass_con_configuracion_completa() -> None:
    fs = FSEnMemoria(
        {
            "/repo/main.py": "def main():\n    return 1",
            "/repo/app/bootstrap/logging.py": "RotatingFileHandler\ncrashes.log",
            "/repo/app/application/caso.py": "def correr():\n    return 1",
        }
    )

    resultado = evaluar_check_logging(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.PASS


def test_evaluar_check_windows_repro_pass_y_fail() -> None:
    fs_ok = FSEnMemoria(
        {
            "/repo/lanzar_app.bat": "echo ok",
            "/repo/ejecutar_tests.bat": "pytest --cov=app",
            "/repo/requirements.txt": "pytest==8.3.2",
            "/repo/requirements-dev.txt": "ruff==0.6.9",
        }
    )
    fs_fail = FSEnMemoria({"/repo/requirements.txt": "pytest>=8.0"})

    assert evaluar_check_windows_repro(fs_ok, Path("/repo")).estado is EstadoCheck.PASS
    assert evaluar_check_windows_repro(fs_fail, Path("/repo")).estado is EstadoCheck.FAIL


def test_evaluar_check_docs_y_versionado_cubren_ramas() -> None:
    fs = FSEnMemoria(
        {
            "/repo/docs/arquitectura.md": "x",
            "/repo/docs/decisiones_tecnicas.md": "x",
            "/repo/docs/guia_pruebas.md": "x",
            "/repo/docs/guia_logging.md": "x",
            "/repo/docs/definicion_producto_final.md": "x",
            "/repo/VERSION": "1.2.3\n",
            "/repo/CHANGELOG.md": "## [1.2.3] - 2026-03-01\n- ok\n",
        }
    )
    fs_sin_version = FSEnMemoria({"/repo/VERSION": "1.2.3"})

    assert evaluar_check_docs(fs, Path("/repo")).estado is EstadoCheck.PASS
    assert evaluar_check_versionado(fs, Path("/repo")).estado is EstadoCheck.PASS
    assert evaluar_check_versionado(fs_sin_version, Path("/repo")).estado is EstadoCheck.FAIL


def test_requirements_pinneados_rechaza_operadores_y_acepta_flags() -> None:
    fs = FSEnMemoria(
        {
            "/repo/ok.txt": "\n# comentario\n-r base.txt\n--extra-index-url x\npaquete==1.0.0\n",
            "/repo/no.txt": "paquete>=1.0.0\n",
        }
    )

    assert _requirements_pinneados(fs, Path("/repo/ok.txt")) is True
    assert _requirements_pinneados(fs, Path("/repo/no.txt")) is False
    assert _requirements_pinneados(fs, Path("/repo/missing.txt")) is False
