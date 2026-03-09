from __future__ import annotations

import logging

from app.application.comunidad.puertos import RepositorioComunidadPuerto
from app.domain.comunidad_descubrimiento import FiltroDescubrimiento, ResultadoDescubrimiento

logger = logging.getLogger(__name__)


class DescubrirComunidadCasoUso:
    def __init__(self, repositorio: RepositorioComunidadPuerto) -> None:
        self._repositorio = repositorio

    def ejecutar(self, filtro: FiltroDescubrimiento) -> ResultadoDescubrimiento:
        try:
            publicaciones = tuple(self._repositorio.listar_publicaciones(filtro))
            disciplinas = tuple(self._repositorio.listar_disciplinas_disponibles())
            perfiles = tuple(self._repositorio.listar_perfiles_sugeridos())
            return ResultadoDescubrimiento(
                publicaciones=publicaciones,
                disciplinas=disciplinas,
                perfiles_sugeridos=perfiles,
                pestaña_siguiendo_habilitada=False,
            )
        except Exception:  # noqa: BLE001
            logger.exception("descubrimiento_comunidad_fallido", extra={"orden": filtro.orden})
            raise
