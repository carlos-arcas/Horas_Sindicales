from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path("app/ui/vistas/main_window/validacion_preventiva.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("validacion_preventiva_pura_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_es_fecha_iso_valida_con_formato_correcto() -> None:
    module = _load_module()
    assert module.es_fecha_iso_valida("2024-12-31") is True


def test_es_fecha_iso_valida_rechaza_fecha_invalida() -> None:
    module = _load_module()
    assert module.es_fecha_iso_valida("2024-02-30") is False
    assert module.es_fecha_iso_valida("31-12-2024") is False


def test_validar_tramo_preventivo_ok_para_jornada_parcial() -> None:
    module = _load_module()
    assert module.validar_tramo_preventivo("09:00", "12:00", False) is None


def test_validar_tramo_preventivo_detecta_error() -> None:
    module = _load_module()
    detalle = module.validar_tramo_preventivo("12:00", "09:00", False)
    assert isinstance(detalle, str)
    assert detalle


def test_validar_tramo_preventivo_acepta_completo() -> None:
    module = _load_module()
    assert module.validar_tramo_preventivo(None, None, True) is None
