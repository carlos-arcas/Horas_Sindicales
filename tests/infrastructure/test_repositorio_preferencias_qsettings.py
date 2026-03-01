from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from aplicacion.preferencias_claves import ONBOARDING_COMPLETADO, PANTALLA_COMPLETA
from infraestructura.repositorio_preferencias_qsettings import RepositorioPreferenciasQSettings


def _build_repo(tmp_path: Path) -> RepositorioPreferenciasQSettings:
    settings_file = tmp_path / "preferencias.ini"
    settings = QSettings(str(settings_file), QSettings.IniFormat)
    return RepositorioPreferenciasQSettings(settings=settings)


def test_round_trip_onboarding_y_pantalla_completa(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    repo.guardar_bool(ONBOARDING_COMPLETADO, True)
    repo.guardar_bool(PANTALLA_COMPLETA, False)

    repo_lectura = _build_repo(tmp_path)

    assert repo_lectura.obtener_bool(ONBOARDING_COMPLETADO, por_defecto=False) is True
    assert repo_lectura.obtener_bool(PANTALLA_COMPLETA, por_defecto=True) is False


def test_defaults_para_claves_inexistentes_migracion_suave(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    assert repo.obtener_bool("clave/no_existe", por_defecto=False) is False
    assert repo.obtener_bool("otra_clave/no_existe", por_defecto=True) is True


def test_lectura_legacy_string_bool_desde_ini(tmp_path: Path) -> None:
    settings_file = tmp_path / "preferencias.ini"
    legacy = QSettings(str(settings_file), QSettings.IniFormat)
    legacy.setValue(ONBOARDING_COMPLETADO, "true")
    legacy.setValue(PANTALLA_COMPLETA, "0")
    legacy.sync()

    repo = _build_repo(tmp_path)

    assert repo.obtener_bool(ONBOARDING_COMPLETADO, por_defecto=False) is True
    assert repo.obtener_bool(PANTALLA_COMPLETA, por_defecto=True) is False
