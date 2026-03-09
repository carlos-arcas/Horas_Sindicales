from __future__ import annotations

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


def test_detectar_error_pytest_qt_devuelve_none_si_plugin_disponible(monkeypatch) -> None:
    monkeypatch.setattr(qt_harness, "_importar_modulo", lambda _nombre: None)

    assert qt_harness.detectar_error_pytest_qt() is None


def test_es_humo_ui_estricto_requiere_flag_y_archivo_conocido(monkeypatch) -> None:
    nodeid_smoke = "tests/ui/test_confirmar_pdf_mainwindow_smoke.py::test_algo"
    monkeypatch.delenv("HORAS_UI_SMOKE_CI", raising=False)
    assert qt_harness._es_humo_ui_estricto(nodeid_smoke) is False

    monkeypatch.setenv("HORAS_UI_SMOKE_CI", "1")
    assert qt_harness._es_humo_ui_estricto(nodeid_smoke) is True
    assert qt_harness._es_humo_ui_estricto("tests/ui/test_otra_cosa.py::test_x") is False


def test_plugin_pytest_qt_define_bloqueo_para_runs_core() -> None:
    assert qt_harness.PLUGIN_PYTEST_QT == ("-p", "no:pytestqt", "-p", "no:pytestqt.plugin")
