from __future__ import annotations

import pytest

from app.testing import qt_harness


def test_humo_ui_estricto_activo_depende_de_variable_entorno(monkeypatch) -> None:
    monkeypatch.delenv("HORAS_UI_SMOKE_CI", raising=False)
    assert qt_harness._humo_ui_estricto_activo() is False

    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "1")
    assert qt_harness._humo_ui_estricto_activo() is True


def test_detectar_error_qt_reporta_libgl_si_falta(monkeypatch) -> None:
    def _import_module(_name: str):
        raise ImportError("libGL.so.1: cannot open shared object file")

    monkeypatch.setattr(qt_harness.importlib, "import_module", _import_module)

    mensaje = qt_harness.detectar_error_qt()

    assert mensaje is not None
    assert "libGL.so.1" in mensaje
    assert "libgl1" in mensaje


def test_detectar_error_pytest_qt_reporta_falta_plugin(monkeypatch) -> None:
    def _importar(nombre_modulo: str) -> None:
        if nombre_modulo.startswith("pytestqt"):
            raise ModuleNotFoundError("No module named 'pytestqt'")

    monkeypatch.setattr(qt_harness, "_importar_modulo", _importar)

    mensaje = qt_harness.detectar_error_pytest_qt()

    assert mensaje is not None
    assert "pytest-qt" in mensaje
    assert "pytestqt" in mensaje


def test_detectar_error_pytest_qt_devuelve_none_si_plugin_disponible(
    monkeypatch,
) -> None:
    monkeypatch.setattr(qt_harness, "_importar_modulo", lambda _nombre: None)

    assert qt_harness.detectar_error_pytest_qt() is None


def test_es_humo_ui_estricto_requiere_flag_y_archivo_conocido(monkeypatch) -> None:
    nodeid_smoke = "tests/ui/test_confirmar_pdf_mainwindow_smoke.py::test_algo"
    monkeypatch.delenv("HORAS_UI_SMOKE_CI", raising=False)
    assert qt_harness._es_humo_ui_estricto(nodeid_smoke) is False

    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "1")
    assert qt_harness._es_humo_ui_estricto(nodeid_smoke) is True
    assert (
        qt_harness._es_humo_ui_estricto("tests/ui/test_otra_cosa.py::test_x") is False
    )


def test_plugin_pytest_qt_define_bloqueo_para_runs_core() -> None:
    assert qt_harness.PLUGIN_PYTEST_QT == (
        "-p",
        "no:pytestqt",
        "-p",
        "no:pytestqt.plugin",
    )


def test__construir_args_pytest_core_no_ui_reinyecta_pytest_cov_si_corresponde() -> (
    None
):
    assert qt_harness._construir_args_pytest_core_no_ui(["-q", "-m", "not ui"]) == [
        "-p",
        "no:pytestqt",
        "-p",
        "no:pytestqt.plugin",
        "-q",
        "-m",
        "not ui",
    ]
    assert qt_harness._construir_args_pytest_core_no_ui(
        ["-q"], habilitar_pytest_cov=True
    )[:2] == ["-p", "pytest_cov"]


def test__construir_env_pytest_core_no_ui_fuerza_entorno_contractual() -> None:
    entorno = qt_harness._construir_env_pytest_core_no_ui({"X": "1"})

    assert entorno["X"] == "1"
    assert entorno["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert entorno["PYTEST_CORE_SIN_QT"] == "1"


def test__aplicar_entorno_pytest_core_no_ui_aplica_y_restaura(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.setenv("PYTEST_CORE_SIN_QT", "0")

    with qt_harness._aplicar_entorno_pytest_core_no_ui():
        assert qt_harness.os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert qt_harness.os.environ["PYTEST_CORE_SIN_QT"] == "1"

    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in qt_harness.os.environ
    assert qt_harness.os.environ["PYTEST_CORE_SIN_QT"] == "0"


def test_preparar_entorno_qt_headless_fija_defaults_relevantes(monkeypatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("QT_OPENGL", raising=False)
    monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
    monkeypatch.setattr(qt_harness.platform, "system", lambda: "Linux")

    entorno = qt_harness.preparar_entorno_qt_headless()

    assert entorno["QT_QPA_PLATFORM"] == "offscreen"
    assert entorno["QT_OPENGL"] == "software"
    assert entorno["QT_QUICK_BACKEND"] == "software"


def test_importar_qt_para_interfaz_real_o_omitir_hace_skip_con_contexto_headless(
    monkeypatch,
) -> None:
    def _importar(nombre_modulo: str):
        raise ImportError(f"fallo {nombre_modulo}")

    monkeypatch.setattr(qt_harness, "_importar_modulo", _importar)

    with pytest.raises(pytest.skip.Exception) as excinfo:
        qt_harness.importar_qt_para_interfaz_real_o_omitir()

    mensaje = str(excinfo.value)
    assert "modo headless" in mensaje
    assert "PySide6/Qt no utilizable" in mensaje


def test_detectar_error_qt_valida_stub_qapplication(monkeypatch) -> None:
    class _QtWidgetsStub:
        class QApplication:
            instance = None

        QFileDialog = object()

    class _QtCoreStub:
        QItemSelectionModel = object()

    def _importar(nombre_modulo: str):
        if nombre_modulo == "PySide6.QtWidgets":
            return _QtWidgetsStub
        if nombre_modulo == "PySide6.QtCore":
            return _QtCoreStub
        raise AssertionError(nombre_modulo)

    monkeypatch.setattr(qt_harness, "_importar_modulo", _importar)

    mensaje = qt_harness.detectar_error_qt()

    assert mensaje is not None
    assert "QApplication.instance" in mensaje
