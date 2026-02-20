from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.application.conflicts_service import ConflictsService
from app.application.sheets_service import SheetsService
from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
from app.application.use_cases.alert_engine import AlertEngine
from app.application.use_cases.health_check import HealthCheckUseCase
from app.infrastructure.db import get_connection
from app.infrastructure.health_probes import DefaultConnectivityProbe, SheetsConfigProbe, SQLiteLocalDbProbe
from app.infrastructure.local_config_store import LocalConfigStore
from app.infrastructure.pdf.generador_pdf_reportlab import GeneradorPdfReportlab
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_conflicts_sqlite import SQLiteConflictsRepository
from app.infrastructure.repos_sqlite import (
    CuadranteRepositorySQLite,
    GrupoConfigRepositorySQLite,
    PersonaRepositorySQLite,
    SolicitudRepositorySQLite,
)
from app.infrastructure.seed import seed_if_empty
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_gateway_gspread import SheetsGatewayGspread
from app.infrastructure.sheets_repository import SheetsRepository
from app.infrastructure.sync_sheets_adapter import SyncSheetsAdapter


@dataclass
class AppContainer:
    persona_use_cases: PersonaUseCases
    solicitud_use_cases: SolicitudUseCases
    grupo_use_cases: GrupoConfigUseCases
    sheets_service: SheetsService
    sync_service: SyncSheetsUseCase
    conflicts_service: ConflictsService
    health_check_use_case: HealthCheckUseCase
    alert_engine: AlertEngine


ConnectionFactory = Callable[[], object]


def build_container(connection_factory: ConnectionFactory = get_connection) -> AppContainer:
    connection = connection_factory()
    run_migrations(connection)
    seed_if_empty(connection)

    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    grupo_repo = GrupoConfigRepositorySQLite(connection)
    cuadrante_repo = CuadranteRepositorySQLite(connection)

    base_cuadrantes_service = BaseCuadrantesService(persona_repo, cuadrante_repo)
    base_cuadrantes_service.ensure_for_all_personas()
    persona_use_cases = PersonaUseCases(persona_repo, base_cuadrantes_service)
    generador_pdf = GeneradorPdfReportlab()
    solicitud_use_cases = SolicitudUseCases(solicitud_repo, persona_repo, grupo_repo, generador_pdf)
    grupo_use_cases = GrupoConfigUseCases(grupo_repo)

    config_store = LocalConfigStore()
    sheets_client = SheetsClient()
    sheets_repository = SheetsRepository()
    sheets_gateway = SheetsGatewayGspread(sheets_client, sheets_repository)
    sheets_service = SheetsService(config_store, sheets_gateway)

    sync_port = SyncSheetsAdapter(connection_factory, config_store, sheets_client, sheets_repository)
    sync_service = SyncSheetsUseCase(sync_port)

    health_check_use_case = HealthCheckUseCase(
        SheetsConfigProbe(config_store, sheets_client),
        DefaultConnectivityProbe(),
        SQLiteLocalDbProbe(connection_factory),
    )
    alert_engine = AlertEngine()

    conflicts_repository = SQLiteConflictsRepository(connection)
    conflicts_service = ConflictsService(
        conflicts_repository,
        lambda: config_store.load().device_id if config_store.load() else "",
    )

    return AppContainer(
        persona_use_cases=persona_use_cases,
        solicitud_use_cases=solicitud_use_cases,
        grupo_use_cases=grupo_use_cases,
        sheets_service=sheets_service,
        sync_service=sync_service,
        conflicts_service=conflicts_service,
        health_check_use_case=health_check_use_case,
        alert_engine=alert_engine,
    )
