from __future__ import annotations

from pathlib import Path

from app.application.ports.datos_demo_puerto import ResultadoCargaDemoPuerto
from app.application.use_cases.cargar_datos_demo_caso_uso import CargarDatosDemoCasoUso
from app.infrastructure.cargador_datos_demo_sqlite import CargadorDatosDemoSQLite
from app.infrastructure.db import get_connection
from app.infrastructure.proveedor_dataset_demo import ProveedorDatasetDemo


class _PuertoDemoFake:
    def __init__(self, resultado: ResultadoCargaDemoPuerto) -> None:
        self._resultado = resultado
        self.modos: list[str] = []

    def cargar(self, modo: str) -> ResultadoCargaDemoPuerto:
        self.modos.append(modo)
        return self._resultado


def test_cargar_demo_en_modo_separado_devuelve_ok() -> None:
    puerto = _PuertoDemoFake(
        ResultadoCargaDemoPuerto(ok=True, mensaje_usuario="Demo cargada", acciones_sugeridas=("IR_SOLICITUDES",))
    )
    use_case = CargarDatosDemoCasoUso(puerto)

    resultado = use_case.ejecutar(modo="SEPARADO")

    assert resultado.ok is True
    assert resultado.mensaje_usuario == "Demo cargada"
    assert puerto.modos == ["SEPARADO"]


def test_cargador_demo_idempotente_recrea_dataset(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    cargador = CargadorDatosDemoSQLite(ProveedorDatasetDemo(), db_path)

    primero = cargador.cargar("SEPARADO")
    segundo = cargador.cargar("SEPARADO")

    assert primero.ok is True
    assert segundo.ok is True
    conn = get_connection(db_path)
    try:
        personas = conn.execute("SELECT COUNT(*) FROM personas").fetchone()[0]
        solicitudes = conn.execute("SELECT COUNT(*) FROM solicitudes").fetchone()[0]
    finally:
        conn.close()
    assert personas >= 2
    assert solicitudes >= 6


def test_cargar_demo_error_controlado_en_ruta_no_escribible(tmp_path: Path) -> None:
    ruta_bloqueada = tmp_path / "archivo.txt"
    ruta_bloqueada.write_text("no-directory", encoding="utf-8")
    db_path = ruta_bloqueada / "demo.sqlite"
    cargador = CargadorDatosDemoSQLite(ProveedorDatasetDemo(), db_path)

    resultado = cargador.cargar("SEPARADO")

    assert resultado.ok is False
    assert resultado.detalles is not None
