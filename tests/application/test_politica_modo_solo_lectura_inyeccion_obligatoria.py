from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.application.use_cases.confirmacion_pdf.caso_uso import (
    ConfirmarPendientesPdfCasoUso,
)
from app.application.use_cases.cargar_datos_demo_caso_uso import CargarDatosDemoCasoUso
from app.application.use_cases.exportar_compartir_periodo import ExportarCompartirPeriodoCasoUso
from app.application.use_cases.grupos_config.use_case import GrupoConfigUseCases
from app.application.use_cases.personas.use_case import PersonaUseCases
from app.application.use_cases.politica_modo_solo_lectura import PoliticaModoSoloLectura
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import CrearPendienteCasoUso
from app.application.use_cases.solicitudes.use_case import SolicitudUseCases
from app.bootstrap.container import build_container

RUTA_CARGA_DEMO = Path("app/application/use_cases/cargar_datos_demo_caso_uso.py")
RUTA_EXPORTAR_COMPARTIR = Path("app/application/use_cases/exportar_compartir_periodo.py")
RUTA_GRUPOS_CONFIG = Path("app/application/use_cases/grupos_config/use_case.py")
RUTA_CREAR_PENDIENTE = Path("app/application/use_cases/solicitudes/crear_pendiente_caso_uso.py")
RUTA_PERSONAS = Path("app/application/use_cases/personas/use_case.py")
RUTA_SOLICITUDES = Path("app/application/use_cases/solicitudes/use_case.py")
RUTA_CONFIRMACION = Path("app/application/use_cases/confirmacion_pdf/caso_uso.py")


@pytest.mark.parametrize(
    ("owner", "kwargs"),
    [
        (
            SolicitudUseCases,
            {"repo": Mock(), "persona_repo": Mock(), "fs": Mock()},
        ),
        (
            PersonaUseCases,
            {"repo": Mock()},
        ),
        (
            ConfirmarPendientesPdfCasoUso,
            {
                "repositorio": Mock(),
                "generador_pdf": Mock(),
                "sistema_archivos": Mock(),
            },
        ),
        (
            CrearPendienteCasoUso,
            {
                "repositorio": Mock(),
            },
        ),
        (
            GrupoConfigUseCases,
            {"repo": Mock()},
        ),
        (
            CargarDatosDemoCasoUso,
            {"cargador": Mock()},
        ),
        (
            ExportarCompartirPeriodoCasoUso,
            {"fs": Mock(), "reloj": Mock(), "exportador_pdf": Mock()},
        ),
    ],
)
def test_owners_mutantes_exigen_politica_en_constructor(owner, kwargs: dict[str, object]) -> None:
    with pytest.raises(TypeError, match="politica_modo_solo_lectura"):
        owner(**kwargs)


@pytest.mark.parametrize(
    ("owner", "nombre_parametro"),
    [
        (SolicitudUseCases, "politica_modo_solo_lectura"),
        (PersonaUseCases, "politica_modo_solo_lectura"),
        (ConfirmarPendientesPdfCasoUso, "politica_modo_solo_lectura"),
        (CrearPendienteCasoUso, "politica_modo_solo_lectura"),
        (GrupoConfigUseCases, "politica_modo_solo_lectura"),
        (CargarDatosDemoCasoUso, "politica_modo_solo_lectura"),
        (ExportarCompartirPeriodoCasoUso, "politica_modo_solo_lectura"),
    ],
)
def test_parametro_politica_no_tiene_default(owner, nombre_parametro: str) -> None:
    parametro = inspect.signature(owner).parameters[nombre_parametro]

    assert parametro.default is inspect.Signature.empty
    assert parametro.annotation in (PoliticaModoSoloLectura, "PoliticaModoSoloLectura")


@pytest.mark.parametrize(
    "ruta",
    [
        RUTA_SOLICITUDES,
        RUTA_PERSONAS,
        RUTA_CONFIRMACION,
        RUTA_CREAR_PENDIENTE,
        RUTA_GRUPOS_CONFIG,
        RUTA_CARGA_DEMO,
        RUTA_EXPORTAR_COMPARTIR,
    ],
)
def test_guardarrail_no_reintroduce_fallback_implicito_en_owners(ruta: Path) -> None:
    contenido = ruta.read_text(encoding="utf-8")

    assert "PoliticaModoSoloLectura | None = None" not in contenido
    assert "or crear_politica_modo_solo_lectura()" not in contenido
    assert "default_factory=crear_politica_modo_solo_lectura" not in contenido


def test_bootstrap_inyecta_la_misma_politica_read_only_en_owners_mutantes() -> None:
    def _connection_factory() -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        return connection

    container = build_container(connection_factory=_connection_factory)

    politica_solicitudes = container.solicitud_use_cases._politica_modo_solo_lectura
    politica_personas = container.persona_use_cases._politica_modo_solo_lectura
    politica_confirmacion = container.confirmar_pendientes_pdf_caso_uso.politica_modo_solo_lectura
    politica_crear_pendiente = container.crear_pendiente_caso_uso.politica_modo_solo_lectura
    politica_grupos = container.grupo_use_cases._politica_modo_solo_lectura
    politica_demo = container.cargar_datos_demo_caso_uso._politica_modo_solo_lectura
    politica_exportacion = container.exportar_compartir_periodo_caso_uso._politica_modo_solo_lectura

    assert politica_solicitudes is politica_personas
    assert politica_solicitudes is politica_confirmacion
    assert politica_solicitudes is politica_crear_pendiente
    assert politica_solicitudes is politica_grupos
    assert politica_solicitudes is politica_demo
    assert politica_solicitudes is politica_exportacion
