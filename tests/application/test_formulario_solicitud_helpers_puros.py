from __future__ import annotations

from app.ui.vistas.builders.formulario_solicitud.ayudantes_puros import calcular_altura_compacta_texto


def test_calcular_altura_compacta_texto_suma_componentes() -> None:
    assert calcular_altura_compacta_texto(3, 14, 8, 2) == 52


def test_calcular_altura_compacta_texto_admite_cero_lineas() -> None:
    assert calcular_altura_compacta_texto(0, 18, 6, 4) == 10
