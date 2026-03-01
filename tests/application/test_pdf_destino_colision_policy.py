from __future__ import annotations

from pathlib import Path

from app.application.use_cases.solicitudes.use_case import SolicitudUseCases


class FakeSistemaArchivos:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self._existentes = existentes or set()

    def existe_ruta(self, ruta: Path) -> bool:
        return str(ruta.resolve(strict=False)) in self._existentes

    def existe(self, ruta: Path) -> bool:
        return self.existe_ruta(ruta)


def _build_use_case(existentes: set[str]) -> SolicitudUseCases:
    return SolicitudUseCases(
        repo=object(),
        persona_repo=object(),
        generador_pdf=None,
        fs=FakeSistemaArchivos(existentes),
    )


def test_destino_existente_genera_siguiente_nombre_disponible(tmp_path: Path) -> None:
    destino = tmp_path / "confirmacion.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "confirmacion(1).pdf").resolve(strict=False)),
    }
    use_case = _build_use_case(existentes)

    resolucion = use_case.resolver_destino_pdf(destino, auto_rename=True, overwrite=False)

    assert resolucion.colision_detectada is True
    assert resolucion.ruta_destino == (tmp_path / "confirmacion(2).pdf").resolve(strict=False)


def test_destino_existente_no_sobrescribe_sin_confirmacion_explicita(tmp_path: Path) -> None:
    destino = tmp_path / "confirmacion.pdf"
    existentes = {
        str(destino.resolve(strict=False)),
        str((tmp_path / "confirmacion(1).pdf").resolve(strict=False)),
    }
    use_case = _build_use_case(existentes)

    sin_sobrescribir = use_case.resolver_destino_pdf(destino, auto_rename=True, overwrite=False)
    sobrescribiendo = use_case.resolver_destino_pdf(destino, auto_rename=True, overwrite=True)

    assert sin_sobrescribir.ruta_destino != sin_sobrescribir.ruta_original
    assert sobrescribiendo.ruta_destino == sobrescribiendo.ruta_original
