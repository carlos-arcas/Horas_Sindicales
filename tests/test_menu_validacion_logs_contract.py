from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_menu_validacion_logs_contract() -> None:
    menu = ROOT / "menu_validacion.bat"

    assert menu.exists(), "Debe existir menu_validacion.bat en la raiz"

    content = menu.read_text(encoding="utf-8").lower()

    assert "logs\\menu_tests_env.txt" in content
    assert "where python" in content
    assert "where pytest" in content
    assert "python --version" in content

    assert "ejecutar_tests.bat" in content
    assert "quality_gate.bat" in content

    for option in ("1)", "2)", "3)", "4)", "0)"):
        assert option in content, f"menu_validacion.bat debe contener la opcion {option}"
