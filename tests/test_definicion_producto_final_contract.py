from pathlib import Path


def test_definicion_producto_final_contract() -> None:
    ruta = Path("docs/definicion_producto_final.md")
    assert ruta.exists(), "Falta docs/definicion_producto_final.md; no se puede declarar cierre de Nivel 4."

    contenido = ruta.read_text(encoding="utf-8")
    assert len(contenido) > 800, (
        "docs/definicion_producto_final.md parece incompleto (menos de 800 caracteres); "
        "debe contener la definición auditable completa."
    )

    referencias_obligatorias = [
        "lanzar_app.bat",
        "ejecutar_tests.bat",
        "quality_gate.bat",
        "VERSION",
        "CHANGELOG",
        "crashes.log",
        "seguimiento.log",
        "pytest --cov",
        "Auditor E2E",
        "dry-run",
    ]

    faltantes = [ref for ref in referencias_obligatorias if ref not in contenido]
    assert not faltantes, (
        "docs/definicion_producto_final.md no cumple contrato; faltan referencias obligatorias: "
        + ", ".join(faltantes)
    )
