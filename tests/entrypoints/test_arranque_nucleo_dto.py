from __future__ import annotations

import configparser

from app.entrypoints.arranque_nucleo import ejecutar_arranque_puro



def test_ejecutar_arranque_puro_lee_idioma_y_flags(monkeypatch, tmp_path) -> None:
    ruta = tmp_path / "preferencias.ini"
    parser = configparser.ConfigParser()
    parser["ui"] = {
        "idioma_ui": "en",
        "pantalla_completa": "true",
        "onboarding_completado": "false",
    }
    with ruta.open("w", encoding="utf-8") as fh:
        parser.write(fh)

    monkeypatch.setattr("app.entrypoints.arranque_nucleo._ruta_preferencias", lambda: ruta)

    resultado = ejecutar_arranque_puro()

    assert resultado.idioma_inicial == "en"
    assert resultado.pantalla_completa_inicial is True
    assert resultado.necesita_onboarding is True



def test_ejecutar_arranque_puro_prioriza_env_para_idioma(monkeypatch, tmp_path) -> None:
    ruta = tmp_path / "preferencias.ini"
    ruta.write_text("[ui]\nidioma_ui=es\n", encoding="utf-8")

    monkeypatch.setenv("HORAS_UI_IDIOMA", "en")
    monkeypatch.setattr("app.entrypoints.arranque_nucleo._ruta_preferencias", lambda: ruta)

    resultado = ejecutar_arranque_puro()

    assert resultado.idioma_inicial == "en"
