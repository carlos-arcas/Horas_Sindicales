from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").lower()


def test_windows_scripts_contract_tokens() -> None:
    lanzar = ROOT / "lanzar_app.bat"
    tests = ROOT / "ejecutar_tests.bat"
    setup = ROOT / "setup.bat"
    update = ROOT / "update.bat"

    assert lanzar.exists(), "Debe existir lanzar_app.bat en la raiz"
    assert tests.exists(), "Debe existir ejecutar_tests.bat en la raiz"
    assert setup.exists(), "Debe existir setup.bat en la raiz"
    assert update.exists(), "Debe existir update.bat en la raiz"

    lanzar_text = _read(lanzar)
    tests_text = _read(tests)
    setup_text = _read(setup)
    update_text = _read(update)

    for name, content in (("lanzar_app.bat", lanzar_text), ("ejecutar_tests.bat", tests_text), ("setup.bat", setup_text), ("update.bat", update_text)):
        assert "%~dp0" in content, f"{name} debe usar rutas relativas basadas en %~dp0"
        assert ".venv" in content, f"{name} debe referenciar .venv"
        assert "logs" in content, f"{name} debe crear/usar logs"
        assert "pip install -r requirements.txt" in content, (
            f"{name} debe instalar requirements.txt"
        )

    assert "pip install -r requirements-dev.txt" in tests_text, (
        "ejecutar_tests.bat debe instalar requirements-dev.txt"
    )
    assert "pytest --cov=. --cov-report=term-missing --cov-fail-under=85" in tests_text, (
        "ejecutar_tests.bat debe ejecutar el comando de cobertura contractual"
    )


def test_windows_scripts_setup_update_contract() -> None:
    setup = _read(ROOT / "setup.bat")
    update = _read(ROOT / "update.bat")

    assert "pip install -r requirements.txt" in setup, "setup.bat debe instalar requirements.txt"
    assert ".venv" in setup, "setup.bat debe preparar .venv"
    assert "logs" in setup, "setup.bat debe escribir logs"
    assert "call \"%root_dir%setup.bat\"" in update, "update.bat debe reutilizar setup.bat"
    assert "requirements-dev.txt" in update, "update.bat debe contemplar requirements-dev.txt"
