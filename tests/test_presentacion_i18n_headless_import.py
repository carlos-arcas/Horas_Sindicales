from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest


class _PySide6Blocker:
    def find_spec(self, fullname: str, path: object | None = None, target: object | None = None) -> None:
        if fullname == "PySide6" or fullname.startswith("PySide6."):
            raise ImportError("PySide6 bloqueado para validar import headless")
        return None


def _limpiar_presentacion() -> None:
    for nombre in [mod for mod in list(sys.modules) if mod == "presentacion" or mod.startswith("presentacion.")]:
        sys.modules.pop(nombre, None)


def test_import_presentacion_i18n_headless_no_requiere_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    blocker = _PySide6Blocker()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])
    _limpiar_presentacion()

    presentacion = importlib.import_module("presentacion")
    i18n = importlib.import_module("presentacion.i18n")
    gestor_i18n = i18n.GestorI18N
    i18n_manager = i18n.I18nManager

    assert hasattr(presentacion, "CATALOGO")
    assert gestor_i18n.__module__ == "presentacion.i18n.gestor_i18n"
    assert i18n_manager.__mro__[1] is gestor_i18n


@pytest.mark.ui
def test_i18n_manager_sigue_funcionando_con_qt_si_esta_disponible() -> None:
    pytest.importorskip("PySide6.QtCore", exc_type=ImportError)
    _limpiar_presentacion()

    i18n = importlib.import_module("presentacion.i18n")
    gestor = i18n.I18nManager("es")
    eventos: list[str] = []

    gestor.idioma_cambiado.connect(eventos.append)
    gestor.set_idioma("en")

    assert gestor.qt_disponible is True
    assert eventos == ["en"]
    assert gestor.tr("splash_window.titulo")


def test_guardrail_gestor_i18n_no_importa_pyside6_a_nivel_de_modulo() -> None:
    ruta = Path("presentacion/i18n/gestor_i18n.py")
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))

    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                assert alias.name != "PySide6"
                assert not alias.name.startswith("PySide6.")
        if isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            assert modulo != "PySide6"
            assert not modulo.startswith("PySide6.")
