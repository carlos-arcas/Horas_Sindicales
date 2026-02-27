from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import SheetsConfig
from app.infrastructure import local_config
from app.infrastructure.local_config import SheetsConfigStore


def test_resolve_appdata_dir_usa_variable_de_entorno(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))

    resultado = local_config.resolve_appdata_dir()

    assert resultado == tmp_path / "appdata" / "HorasSindicales"


def test_resolve_appdata_dir_usa_home_si_no_hay_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(local_config.Path, "home", lambda: tmp_path)

    resultado = local_config.resolve_appdata_dir()

    assert resultado == tmp_path / ".local" / "share" / "HorasSindicales"


def test_load_devuelve_none_si_no_existe_config(tmp_path: Path) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)

    assert store.load() is None


def test_load_devuelve_none_con_json_invalido(tmp_path: Path) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)
    (tmp_path / "config.json").write_text("{ invalido", encoding="utf-8")

    assert store.load() is None


def test_load_autogenera_device_id_y_persiste(tmp_path: Path, monkeypatch) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "sheets_spreadsheet_id": "sheet-123",
                "path_credentials_json": "cred.json",
                "device_id": "",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(SheetsConfigStore, "_generate_device_id", staticmethod(lambda: "device-fijo"))

    config = store.load()

    assert config is not None
    assert config.device_id == "device-fijo"
    payload = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert payload["device_id"] == "device-fijo"


def test_load_devuelve_none_si_faltan_rutas_relevantes(tmp_path: Path) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({"sheets_spreadsheet_id": " ", "path_credentials_json": "", "device_id": "abc"}),
        encoding="utf-8",
    )

    assert store.load() is None


def test_save_escribe_config_y_device_id_generado(tmp_path: Path, monkeypatch) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)
    monkeypatch.setattr(SheetsConfigStore, "_generate_device_id", staticmethod(lambda: "device-save"))

    guardado = store.save(SheetsConfig(spreadsheet_id="sheet", credentials_path="cred.json", device_id=""))

    assert guardado.device_id == "device-save"
    payload = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert payload["sheets_spreadsheet_id"] == "sheet"


def test_credentials_path_apunta_a_secrets_credentials(tmp_path: Path) -> None:
    store = SheetsConfigStore(base_dir=tmp_path)

    assert store.credentials_path() == tmp_path / "secrets" / "credentials.json"
