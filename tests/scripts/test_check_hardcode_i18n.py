from __future__ import annotations

from pathlib import Path

from scripts.i18n.check_hardcode_i18n import ConfigCheck, analizar_rutas, renderizar_hallazgos


def _crear_archivo(base: Path, ruta: str, contenido: str) -> None:
    archivo = base / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")


def test_check_i18n_ok_con_clave_fuerte(tmp_path: Path) -> None:
    _crear_archivo(
        tmp_path,
        "app/ui/pantalla.py",
        'def construir(tr):\n    return tr("main_window.boton_ok")\n',
    )
    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    assert hallazgos == []


def test_check_i18n_fail_reporta_linea_correcta(tmp_path: Path) -> None:
    _crear_archivo(
        tmp_path,
        "app/ui/dialogo.py",
        'def build():\n    return "Confirmar acción"\n',
    )
    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    salida = renderizar_hallazgos(hallazgos)

    assert len(hallazgos) == 1
    assert hallazgos[0].lineno == 2
    assert salida == '[I18N_HARDCODE] app/ui/dialogo.py:2 -> "Confirmar acción"'


def test_check_i18n_omite_literal_en_logger(tmp_path: Path) -> None:
    _crear_archivo(
        tmp_path,
        "app/ui/logs_ui.py",
        'def traza(logger):\n    logger.info("evento de depuracion")\n',
    )
    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    assert hallazgos == []


def test_check_i18n_omite_clave_i18n(tmp_path: Path) -> None:
    _crear_archivo(
        tmp_path,
        "app/ui/clave.py",
        'def clave():\n    return "main_window.boton_confirmar"\n',
    )
    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    assert hallazgos == []


def test_check_i18n_render_orden_estable(tmp_path: Path) -> None:
    _crear_archivo(tmp_path, "app/ui/z.py", 'def a():\n    return "Texto Zulu"\n')
    _crear_archivo(tmp_path, "app/ui/a.py", 'def b():\n    return "Texto Alfa"\n')

    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    salida = renderizar_hallazgos(hallazgos).splitlines()

    assert salida == [
        '[I18N_HARDCODE] app/ui/a.py:2 -> "Texto Alfa"',
        '[I18N_HARDCODE] app/ui/z.py:2 -> "Texto Zulu"',
    ]
