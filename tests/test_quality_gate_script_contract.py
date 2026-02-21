from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").lower()


def test_quality_gate_script_contract() -> None:
    script = ROOT / "quality_gate.bat"
    assert script.exists(), "Debe existir quality_gate.bat en la raiz"

    content = _read(script)

    assert "%~dp0" in content, "quality_gate.bat debe usar rutas relativas con %~dp0"
    assert ".venv" in content, "quality_gate.bat debe crear/usar .venv"
    assert "pip install -r requirements-dev.txt" in content, (
        "quality_gate.bat debe instalar requirements-dev.txt"
    )
    assert "python scripts/preflight_tests.py" in content, (
        "quality_gate.bat debe ejecutar preflight_tests.py antes del gate"
    )
    assert "python -m app.entrypoints.cli_auditoria --dry-run" in content, (
        "quality_gate.bat debe ejecutar auditoria e2e en dry-run"
    )
    assert "pytest --cov=. --cov-report=term-missing --cov-fail-under=85" in content, (
        "quality_gate.bat debe ejecutar pytest con cobertura y umbral"
    )
    assert content.index("python scripts/preflight_tests.py") < content.index("pytest --cov=. --cov-report=term-missing --cov-fail-under=85"), (
        "quality_gate.bat debe correr preflight antes de pytest"
    )
    assert "quality_gate_stdout.log" in content, "quality_gate.bat debe redirigir stdout a logs"
    assert "quality_gate_stderr.log" in content, "quality_gate.bat debe redirigir stderr a logs"
    assert "quality_gate_debug.log" in content, "quality_gate.bat debe escribir log de debug"
