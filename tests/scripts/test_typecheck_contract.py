from __future__ import annotations

from pathlib import Path

from scripts import typecheck


def test_typecheck_falla_con_error_claro_si_falta_mypy(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setattr(typecheck, "_mypy_disponible", lambda: False)
    monkeypatch.setattr(
        typecheck.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("No debe ejecutar mypy si no está instalado")
        ),
    )

    resultado = typecheck.main()

    assert resultado == 1
    assert "ERROR: falta mypy en requirements-dev.txt" in caplog.text


def test_requirements_dev_incluye_mypy_con_version_fijada() -> None:
    contenido = Path("requirements-dev.txt").read_text(encoding="utf-8")
    assert "mypy==" in contenido
