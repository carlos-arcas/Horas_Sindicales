from __future__ import annotations

from infraestructura.i18n.proveedor_traducciones import ProveedorTraducciones


def test_traduce_clave_existente() -> None:
    proveedor = ProveedorTraducciones("es")

    assert proveedor.traducir("splash_window.titulo") == "Iniciando Horas Sindicales…"


def test_fallback_a_idioma_base_para_clave_faltante_en_idioma_actual() -> None:
    proveedor = ProveedorTraducciones("en")
    proveedor.catalogos["en"].pop("splash_window.titulo", None)

    assert proveedor.traducir("splash_window.titulo") == "Iniciando Horas Sindicales…"


def test_clave_inexistente_devuelve_marcador() -> None:
    proveedor = ProveedorTraducciones("es")

    assert proveedor.traducir("inexistente.total") == "[i18n:inexistente.total]"
