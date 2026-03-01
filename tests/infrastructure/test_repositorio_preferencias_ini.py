from __future__ import annotations

from pathlib import Path

from app.infrastructure.local_config import RepositorioPreferenciasIni
from aplicacion.preferencias_claves import PANTALLA_COMPLETA


def test_round_trip_preferencia_pantalla_completa_ini(tmp_path: Path) -> None:
    ruta = tmp_path / "preferencias.ini"

    repo = RepositorioPreferenciasIni(ruta)
    assert repo.obtener_bool(PANTALLA_COMPLETA, por_defecto=False) is False

    repo.guardar_bool(PANTALLA_COMPLETA, True)

    repo_lectura = RepositorioPreferenciasIni(ruta)
    assert repo_lectura.obtener_bool(PANTALLA_COMPLETA, por_defecto=False) is True
