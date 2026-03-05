from __future__ import annotations

from app.bootstrap.logging import truncar_archivo


def test_truncar_archivo_vacia_seguimiento_log(tmp_path) -> None:
    ruta_log = tmp_path / "logs" / "seguimiento.log"
    ruta_log.parent.mkdir(parents=True, exist_ok=True)
    ruta_log.write_text("contenido previo", encoding="utf-8")

    truncar_archivo(ruta_log)

    assert ruta_log.exists()
    assert ruta_log.stat().st_size == 0


def test_truncar_archivo_vacia_crashes_log(tmp_path) -> None:
    ruta_log = tmp_path / "logs" / "crashes.log"
    ruta_log.parent.mkdir(parents=True, exist_ok=True)
    ruta_log.write_text("contenido previo", encoding="utf-8")

    truncar_archivo(ruta_log)

    assert ruta_log.exists()
    assert ruta_log.stat().st_size == 0
