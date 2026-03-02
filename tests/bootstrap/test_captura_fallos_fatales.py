from __future__ import annotations

from pathlib import Path

from app.bootstrap import captura_fallos_fatales as modulo


def test_iniciar_captura_crea_archivos(tmp_path: Path) -> None:
    modulo.iniciar_captura_fallos_fatales(log_dir=tmp_path, sobrescribir=True)

    assert (tmp_path / "crashes.log").exists()
    assert (tmp_path / "seguimiento.log").exists()


def test_marcar_stage_escribe_en_seguimiento(tmp_path: Path) -> None:
    modulo.iniciar_captura_fallos_fatales(log_dir=tmp_path, sobrescribir=True)

    modulo.marcar_stage("UI_BOOT_INICIO")

    contenido = (tmp_path / "seguimiento.log").read_text(encoding="utf-8")
    assert "BOOT_STAGE=UI_BOOT_INICIO" in contenido


def test_sys_excepthook_escribe_en_crashes(tmp_path: Path) -> None:
    modulo.iniciar_captura_fallos_fatales(log_dir=tmp_path, sobrescribir=True)

    try:
        raise RuntimeError("fallo controlado de prueba")
    except RuntimeError as exc:
        modulo.sys.excepthook(type(exc), exc, exc.__traceback__)

    contenido = (tmp_path / "crashes.log").read_text(encoding="utf-8")
    assert "RuntimeError: fallo controlado de prueba" in contenido
