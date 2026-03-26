from __future__ import annotations

from scripts import gate_rapido


def test_comando_pytest_core_no_ui_reutiliza_harness() -> None:
    comando, entorno = gate_rapido._comando_pytest_core_no_ui(
        ["-q", "tests/domain", "tests/application"]
    )

    assert comando[:8] == [
        gate_rapido.PYTHON_BIN,
        "-m",
        "pytest",
        "-p",
        "no:pytestqt",
        "-p",
        "no:pytestqt.plugin",
        "-q",
    ]
    assert comando[8:] == ["tests/domain", "tests/application"]
    assert entorno["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert entorno["PYTEST_CORE_SIN_QT"] == "1"


def test_main_inyecta_entorno_core_no_ui_en_subruns_pytest(monkeypatch) -> None:
    llamadas: list[tuple[list[str], dict[str, str] | None]] = []

    def _run_falso(cmd: list[str], env: dict[str, str] | None = None) -> int:
        llamadas.append((cmd, env))
        return 0

    monkeypatch.setattr(gate_rapido, "_run", _run_falso)

    assert gate_rapido.main() == 0

    comandos_pytest = [
        (cmd, env)
        for cmd, env in llamadas
        if cmd[:3] == [gate_rapido.PYTHON_BIN, "-m", "pytest"]
    ]

    assert len(comandos_pytest) == 2
    for cmd, env in comandos_pytest:
        assert env is not None
        assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert env["PYTEST_CORE_SIN_QT"] == "1"
        assert "no:pytestqt" in cmd
        assert "no:pytestqt.plugin" in cmd
