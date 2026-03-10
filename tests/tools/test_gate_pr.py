from __future__ import annotations

from scripts import gate_pr


def test_comando_pytest_core_no_ui_reutiliza_harness_con_pytest_cov() -> None:
    comando, entorno = gate_pr._comando_pytest_core_no_ui(
        ["-q", "tests/domain", "tests/application"],
        habilitar_pytest_cov=True,
    )

    assert comando[:8] == [
        gate_pr.sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_cov",
        "-p",
        "no:pytestqt",
        "-p",
    ]
    assert comando[8:10] == ["no:pytestqt.plugin", "-q"]
    assert entorno["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert entorno["PYTEST_CORE_SIN_QT"] == "1"


def test_main_blinda_subruns_core_no_ui_post_ruff(monkeypatch) -> None:
    llamadas: list[tuple[list[str], dict[str, str] | None]] = []

    def _run_falso(cmd: list[str], env: dict[str, str] | None = None) -> int:
        llamadas.append((cmd, env))
        return 0

    monkeypatch.setattr(gate_pr, "_run", _run_falso)
    monkeypatch.setattr(gate_pr.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(gate_pr.subprocess, "run", lambda *_args, **_kwargs: type("R", (), {"returncode": 0})())

    exit_code = gate_pr.main()

    assert exit_code == 0

    comandos_pytest = [
        (cmd, env)
        for cmd, env in llamadas
        if cmd[:3] == [gate_pr.sys.executable, "-m", "pytest"]
    ]

    assert comandos_pytest
    for cmd, env in comandos_pytest:
        es_ui = "tests/golden/botones" in cmd
        if es_ui:
            assert env is None
            continue
        assert env is not None
        assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert env["PYTEST_CORE_SIN_QT"] == "1"
        assert "-p" in cmd
        assert "no:pytestqt" in cmd
        assert "no:pytestqt.plugin" in cmd


def test_main_reinyecta_pytest_cov_solo_en_coverage(monkeypatch) -> None:
    llamadas: list[list[str]] = []

    def _run_falso(cmd: list[str], env: dict[str, str] | None = None) -> int:
        if cmd[:3] == [gate_pr.sys.executable, "-m", "pytest"]:
            llamadas.append(cmd)
        return 0

    monkeypatch.setattr(gate_pr, "_run", _run_falso)
    monkeypatch.setattr(gate_pr.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(gate_pr.subprocess, "run", lambda *_args, **_kwargs: type("R", (), {"returncode": 0})())

    assert gate_pr.main() == 0

    invocaciones_con_cov = [cmd for cmd in llamadas if "--cov=app/domain" in cmd]
    assert len(invocaciones_con_cov) == 1
    assert invocaciones_con_cov[0].count("pytest_cov") == 1

    invocaciones_sin_cov = [cmd for cmd in llamadas if "--cov=app/domain" not in cmd]
    assert invocaciones_sin_cov
    for cmd in invocaciones_sin_cov:
        assert "pytest_cov" not in cmd
