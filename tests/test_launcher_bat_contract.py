from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_bat_contract() -> None:
    launcher = ROOT / "launcher.bat"

    assert launcher.exists(), "launcher.bat debe existir en la raiz"

    content = launcher.read_text(encoding="utf-8", errors="ignore").lower()

    assert "%~dp0" in content, "launcher.bat debe usar rutas relativas con %~dp0"
    assert "lanzar_app.bat" in content, "launcher.bat debe delegar en lanzar_app.bat"
    assert "ejecutar_tests.bat" in content, "launcher.bat debe delegar en ejecutar_tests.bat"
    assert "quality_gate.bat" in content, "launcher.bat debe delegar en quality_gate.bat"
    assert ("auditar" in content) or ("cli_auditoria" in content), (
        "launcher.bat debe incluir una opcion de auditoria e2e"
    )

    menu_tokens = ("1)", "2)", "3)", "4)", "5)", "0)")
    options_found = sum(1 for token in menu_tokens if token in content)
    assert options_found >= 4, "launcher.bat debe contener al menos 4 opciones de menu"
