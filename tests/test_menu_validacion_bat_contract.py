from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_menu_validacion_bat_contract() -> None:
    menu = ROOT / "menu_validacion.bat"

    assert menu.exists(), "Debe existir menu_validacion.bat en la raiz"

    content = menu.read_text(encoding="utf-8").lower()

    assert "%~dp0" in content, "menu_validacion.bat debe usar rutas relativas con %~dp0"
    assert "ejecutar_tests.bat" in content, "menu_validacion.bat debe delegar en ejecutar_tests.bat"
    assert "quality_gate.bat" in content, "menu_validacion.bat debe delegar en quality_gate.bat"
    assert "logs\\menu_ultima_ejecucion.txt" in content, (
        "menu_validacion.bat debe escribir logs\\menu_ultima_ejecucion.txt"
    )

    for option in ("1)", "2)", "3)", "0)"):
        assert option in content, f"menu_validacion.bat debe contener la opcion {option}"

    assert "powershell" not in content, "menu_validacion.bat no debe usar powershell"
