from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

BLOQUEADOS = ("PySide6", "app.ui")
MODULOS_PRESENTACION = tuple(
    nombre for nombre in sys.modules if nombre == "presentacion" or nombre.startswith("presentacion.")
)


@contextmanager
def _bloquear_imports_ui() -> Iterator[None]:
    original_import = builtins.__import__

    def import_guard(name: str, *args, **kwargs):
        if name.startswith(BLOQUEADOS):
            raise AssertionError(f"Import bloqueado en modo headless: {name}")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = import_guard
    try:
        yield
    finally:
        builtins.__import__ = original_import


@pytest.fixture
def limpiar_modulos_presentacion() -> Iterator[None]:
    for nombre in MODULOS_PRESENTACION:
        sys.modules.pop(nombre, None)
    yield
    for nombre in tuple(sys.modules):
        if nombre == "presentacion" or nombre.startswith("presentacion."):
            sys.modules.pop(nombre, None)


def test_import_presentacion_no_toca_dependencias_ui(limpiar_modulos_presentacion) -> None:
    with _bloquear_imports_ui():
        modulo = importlib.import_module("presentacion")

    assert modulo is not None


def test_import_presentacion_i18n_no_toca_dependencias_ui(limpiar_modulos_presentacion) -> None:
    with _bloquear_imports_ui():
        modulo = importlib.import_module("presentacion.i18n")

    assert modulo is not None
