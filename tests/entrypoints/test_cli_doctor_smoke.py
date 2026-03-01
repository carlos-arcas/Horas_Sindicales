from __future__ import annotations

import json

from app.entrypoints.cli_doctor import EXIT_OK, main


def test_cli_doctor_main_ok_with_minimal_local_setup(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HORAS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))

    base_dir = tmp_path / "appdata" / "HorasSindicales"
    credentials = base_dir / "secrets" / "credentials.json"
    credentials.parent.mkdir(parents=True, exist_ok=True)
    credentials.write_text("{}", encoding="utf-8")

    config_path = base_dir / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "sheets_spreadsheet_id": "spreadsheet-id-presente",
                "path_credentials_json": str(credentials),
                "device_id": "device-test",
            }
        ),
        encoding="utf-8",
    )

    result = main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == EXIT_OK
    assert payload["exit_code"] == EXIT_OK
    assert [check["status"] for check in payload["checks"]] == ["ok", "ok", "ok"]
