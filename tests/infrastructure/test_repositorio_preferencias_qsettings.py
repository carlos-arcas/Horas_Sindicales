from __future__ import annotations

from pathlib import Path

import pytest
QSettings = pytest.importorskip("PySide6.QtCore", exc_type=ImportError).QSettings

from aplicacion.preferencias_claves import INICIAR_MAXIMIZADA, INICIAR_MAXIMIZADA_LEGACY, ONBOARDING_COMPLETADO
from infraestructura.repositorio_preferencias_qsettings import RepositorioPreferenciasQSettings

pytestmark = pytest.mark.ui


def _build_repo(tmp_path: Path) -> RepositorioPreferenciasQSettings:
    settings_file = tmp_path / "preferencias.ini"
    settings = QSettings(str(settings_file), QSettings.IniFormat)
    return RepositorioPreferenciasQSettings(settings=settings)


def test_round_trip_onboarding_y_inicio_maximizado(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    repo.guardar_bool(ONBOARDING_COMPLETADO, True)
    repo.guardar_bool(INICIAR_MAXIMIZADA, False)

    repo_lectura = _build_repo(tmp_path)

    assert repo_lectura.obtener_bool(ONBOARDING_COMPLETADO, por_defecto=False) is True
    assert repo_lectura.obtener_bool(INICIAR_MAXIMIZADA, por_defecto=True) is False


def test_defaults_para_claves_inexistentes_migracion_suave(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    assert repo.obtener_bool("clave/no_existe", por_defecto=False) is False
    assert repo.obtener_bool("otra_clave/no_existe", por_defecto=True) is True


def test_lectura_legacy_string_bool_desde_ini(tmp_path: Path) -> None:
    settings_file = tmp_path / "preferencias.ini"
    legacy = QSettings(str(settings_file), QSettings.IniFormat)
    legacy.setValue(ONBOARDING_COMPLETADO, "true")
    legacy.setValue(INICIAR_MAXIMIZADA_LEGACY, "0")
    legacy.sync()

    repo = _build_repo(tmp_path)

    assert repo.obtener_bool(ONBOARDING_COMPLETADO, por_defecto=False) is True
    assert repo.obtener_bool(INICIAR_MAXIMIZADA, por_defecto=True) is False


def test_guardar_inicio_maximizado_persiste_en_clave_nueva(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    repo.guardar_bool(INICIAR_MAXIMIZADA, True)

    settings = QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)
    assert settings.value(INICIAR_MAXIMIZADA) is True
    assert settings.contains(INICIAR_MAXIMIZADA)


def test_lectura_prioriza_clave_nueva_sobre_legacy(tmp_path: Path) -> None:
    settings = QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)
    settings.setValue(INICIAR_MAXIMIZADA_LEGACY, True)
    settings.setValue(INICIAR_MAXIMIZADA, False)
    settings.sync()

    repo = _build_repo(tmp_path)

    assert repo.obtener_bool(INICIAR_MAXIMIZADA, por_defecto=True) is False
