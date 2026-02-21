from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").lower()


def test_windows_scripts_contract_tokens() -> None:
    lanzar = ROOT / "lanzar_app.bat"
    tests = ROOT / "ejecutar_tests.bat"

    assert lanzar.exists(), "Debe existir lanzar_app.bat en la raiz"
    assert tests.exists(), "Debe existir ejecutar_tests.bat en la raiz"

    lanzar_text = _read(lanzar)
    tests_text = _read(tests)

    for name, content in (("lanzar_app.bat", lanzar_text), ("ejecutar_tests.bat", tests_text)):
        assert "%~dp0" in content, f"{name} debe usar rutas relativas basadas en %~dp0"
        assert ".venv" in content, f"{name} debe referenciar .venv"
        assert "logs" in content, f"{name} debe crear/usar logs"
        assert "pip install -r requirements.txt" in content, (
            f"{name} debe instalar requirements.txt"
        )

    assert "pip install -r requirements-dev.txt" in tests_text, (
        "ejecutar_tests.bat debe instalar requirements-dev.txt"
    )
    assert "python -m pytest -q tests --cov=app --cov-report=term-missing" in tests_text, (
        "ejecutar_tests.bat debe ejecutar pytest con cobertura sobre app"
    )
    assert "--cov-fail-under" not in tests_text, (
        "ejecutar_tests.bat no debe aplicar quality gate de cobertura"
    )
