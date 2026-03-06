from __future__ import annotations

from pathlib import Path

from scripts.i18n.check_hardcode_i18n import ConfigCheck, analizar_ruta


RUTA_CONTRATO_RUNTIME = Path("app/ui/vistas/main_window/contrato_senales_runtime.py")


def test_contrato_senales_runtime_no_reintroduce_contexto_colon_detectable() -> None:
    hallazgos = analizar_ruta(RUTA_CONTRATO_RUNTIME, ConfigCheck())
    textos_hallados = {item.texto for item in hallazgos}

    assert "contrato_senales:" not in textos_hallados
    assert "contrato_senales:." not in textos_hallados
