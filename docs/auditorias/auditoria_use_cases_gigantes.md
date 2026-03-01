# Auditoría de casos de uso gigantes

## Alcance y criterio

Ruta auditada: `app/application/use_cases/**/*`.

Se consideró **gigante** cualquier unidad que cumpla al menos una condición:
- Archivo con más de 300 LOC.
- Función/método con más de 40 LOC.
- Complejidad ciclomática (CC) estimada mayor a 10.

> Nota: la CC aquí es una estimación estática (AST) para priorización de refactor, no un reemplazo de una herramienta formal de calidad.

---

## 1) Top 5 archivos más grandes

| Rank | Archivo | LOC (no vacías) | Diagnóstico rápido |
|---|---|---:|---|
| 1 | `app/application/use_cases/sync_sheets/use_case.py` | 1147 | Orquestador monolítico con mezcla de planner, runner, persistencia y reporting. |
| 2 | `app/application/use_cases/solicitudes/use_case.py` | 824 | Caso de uso multipropósito (CRUD, validación, confirmación, PDF, saldos). |
| 3 | `app/application/use_cases/sync_sheets_core.py` | 271 | No supera 300 LOC no vacías, pero concentra reglas y normalización transversales. |
| 4 | `app/application/use_cases/sync_sheets/helpers.py` | 243 | Helpers con planificación + ejecución/persistencia local implícita. |
| 5 | `app/application/use_cases/personas/use_case.py` | 203 | Fábrica/ensamblado DTO y lógica de caso de uso en el mismo módulo. |

### Responsabilidades mezcladas por archivo

#### A. `sync_sheets/use_case.py`
- **validación**: chequeos de conexión, filtros y condiciones previas.
- **normalización/mapeo DTO**: parseo y normalización de filas remotas/locales.
- **planificación (planner)**: armado de planes de pull/push y resolución de acciones.
- **ejecución (runner)**: ejecución de acciones contra repositorios y hojas.
- **persistencia (repositorios)**: inserciones/updates de delegadas, solicitudes, cuadrantes y config.
- **reporting/auditoría**: métricas, conflicto, trazas de sync y batching.
- **composición/orquestación**: coordina todas las piezas dentro de una sola clase gigante.

#### B. `solicitudes/use_case.py`
- **validación**: validaciones de entrada, conflictos, duplicados y reglas de negocio.
- **normalización/mapeo DTO**: construcción/normalización de DTOs para crear/confirmar/exportar.
- **planificación (planner)**: armado de lotes de confirmación y criterios de exportación.
- **ejecución (runner)**: confirmaciones, operaciones de repositorio y generación de salidas.
- **persistencia (repositorios)**: altas/bajas/modificaciones de solicitudes y consultas de saldos.
- **reporting/auditoría**: logs operativos/correlation id, resumen de saldos, metadata PDF.
- **composición/orquestación**: fachada enorme que concentra demasiados flujos.

#### C. `sync_sheets_core.py`
- **validación**: validación de campos requeridos y formatos.
- **normalización/mapeo DTO**: coerción y canonicalización de payloads.
- **planificación/ejecución**: menor, pero reglas usadas por planners/runners sin contrato explícito.
- **composición/orquestación**: acoplamiento implícito por funciones utilitarias compartidas.

#### D. `sync_sheets/helpers.py`
- **validación**: verificaciones en armado de plan y campos.
- **normalización/mapeo DTO**: normalización de fechas y payloads.
- **planificación (planner)**: `build_solicitudes_sync_plan`.
- **ejecución (runner)**: `sync_local_cuadrantes_from_personas` modifica estado local.
- **persistencia**: efectos laterales locales mezclados con cálculo.
- **composición/orquestación**: helper híbrido (pureza no consistente).

#### E. `personas/use_case.py`
- **normalización/mapeo DTO**: mapeos `_persona_to_dto`, `_dto_to_persona`, factory formulario.
- **validación**: normalización de cuadrantes y consistencia de campos.
- **persistencia**: operaciones del caso de uso `PersonaUseCases`.
- **composición/orquestación**: módulo combina fábrica + servicio + mapeo sin límites nítidos.

---

## 2) Top 10 funciones/métodos más grandes

| Rank | Unidad | LOC | CC estimada | Marca “gigante” | Responsabilidades mezcladas |
|---|---|---:|---:|---|---|
| 1 | `sync_sheets/helpers.py::build_solicitudes_sync_plan` | 64 | 10 | LOC>40 | planificación + validación + normalización + composición |
| 2 | `solicitudes/pdf_confirmadas_runner.py::run_pdf_confirmadas_plan` | 62 | 18 | LOC>40 y CC>10 | ejecución + reporting + persistencia + composición |
| 3 | `sync_sheets/helpers.py::sync_local_cuadrantes_from_personas` | 61 | 11 | LOC>40 y CC>10 | ejecución + persistencia + validación |
| 4 | `alert_engine.py::evaluate` | 57 | 10 | LOC>40 | validación + reglas + reporting |
| 5 | `sync_sheets/use_case.py::_push_cuadrantes` | 48 | 10 | LOC>40 | planner local + ejecución + persistencia + orquestación |
| 6 | `solicitudes/use_case.py::confirmar_lote_y_generar_pdf` | 48 | 7 | LOC>40 | planificación + ejecución + reporting + composición |
| 7 | `sync_sheets/ayudantes_push.py::push_delegadas` | 46 | 13 | LOC>40 y CC>10 | ejecución + persistencia + validación |
| 8 | `personas/use_case.py::PersonaFactory.desde_formulario` | 44 | 1 | LOC>40 | normalización DTO + validación + ensamblado |
| 9 | `sync_sheets/push_builder.py::build_push_solicitudes_payloads` | 42 | 10 | LOC>40 | planificación + normalización + composición |
| 10 | `solicitudes/use_case.py::exportar_historico_pdf` | 42 | 10 | LOC>40 | planificación + ejecución + reporting |

---

## 3) Plan de extracción por módulos nuevos (<300 LOC)

## Principios de corte
1. Separar por responsabilidad operativa (reglas/planner/runner/ensamblado/puertos).
2. Mantener compatibilidad de API pública en primera fase (fachada delega en nuevos módulos).
3. Limitar tamaño objetivo por archivo: **120–250 LOC**, tope absoluto 300.
4. Priorizar primero los “hotspots” con mayor mezcla de responsabilidades.

### 3.1 Refactor propuesto para `sync_sheets/use_case.py`

**Módulos nuevos sugeridos**
- `app/application/use_cases/sync_sheets/pull_planner.py` (ampliar lo existente).
- `app/application/use_cases/sync_sheets/pull_runner.py` (ampliar lo existente).
- `app/application/use_cases/sync_sheets/push_planner.py` (nuevo o ampliar `action_planning.py`).
- `app/application/use_cases/sync_sheets/push_runner.py` (ampliar lo existente).
- `app/application/use_cases/sync_sheets/sync_reglas.py` (puras).
- `app/application/use_cases/sync_sheets/sync_ensamblador.py` (DTO interno y payloads).
- `app/application/use_cases/sync_sheets/sync_puertos.py` (interfaces/Protocol de gateways/repos).
- `app/application/use_cases/sync_sheets/sync_auditoria.py` (reporting y métricas).

**Cortes atómicos sugeridos**
1. Extraer contratos y tipos compartidos (`sync_contratos.py`) sin cambiar flujos.
2. Mover funciones puras de normalización/reglas a `sync_reglas.py`.
3. Mover armado de planes pull/push a planners dedicados.
4. Mover ejecución de acciones (DB/Sheets) a runners.
5. Mover batching y telemetría a `sync_auditoria.py`.
6. Dejar `SheetsSyncService` como orquestador delgado (delegación).

### 3.2 Refactor propuesto para `solicitudes/use_case.py`

**Módulos nuevos sugeridos**
- `app/application/use_cases/solicitudes/confirmacion_planner.py`.
- `app/application/use_cases/solicitudes/confirmacion_runner.py`.
- `app/application/use_cases/solicitudes/solicitudes_reglas.py`.
- `app/application/use_cases/solicitudes/solicitudes_ensamblador.py`.
- `app/application/use_cases/solicitudes/solicitudes_puertos.py`.
- `app/application/use_cases/solicitudes/reporting_auditoria.py`.

**Cortes atómicos sugeridos**
1. Extraer reglas puras de conflicto/duplicado/saldos a `solicitudes_reglas.py`.
2. Extraer ensamblado DTO de creación/confirmación/exportación.
3. Extraer planificador de confirmación por lote y exportación histórica.
4. Extraer runner de confirmación y generación de PDF (sin tocar algoritmos).
5. Extraer puertos explícitos de repositorio y servicio PDF.
6. Reducir `SolicitudUseCases` a coordinación y políticas transversales.

### 3.3 Refactor propuesto para funciones gigantes puntuales

- `build_solicitudes_sync_plan` → dividir en:
  - `solicitudes_sync_planner.py::construir_plan_solicitudes`
  - `solicitudes_sync_reglas.py::detectar_diferencias_solicitud`
  - `solicitudes_sync_ensamblador.py::armar_accion_sync`
- `sync_local_cuadrantes_from_personas` → dividir en:
  - `cuadrantes_runner.py::sincronizar_cuadrantes_locales`
  - `cuadrantes_reglas.py::calcular_minutos_cuadrante`
- `confirmar_lote_y_generar_pdf` / `exportar_historico_pdf` → dividir en:
  - `confirmacion_planner.py`
  - `confirmacion_runner.py`
  - `confirmacion_ensamblador.py`
- `PersonaFactory.desde_formulario` → dividir en:
  - `personas_reglas.py::normalizar_formulario_persona`
  - `personas_ensamblador.py::construir_persona_desde_formulario`

---

## 4) Contratos explícitos recomendados (dataclasses / TypedDict)

> Objetivo: eliminar diccionarios “anónimos” entre planner/runner y hacer explícitos los puertos.

### Contratos transversales Sync Sheets

```python
from dataclasses import dataclass
from typing import Literal, TypedDict, Protocol, Optional

class FilaSolicitudRemota(TypedDict, total=False):
    uuid: str
    persona_uuid: str
    nombre: str
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str
    updated_at: str

@dataclass(frozen=True)
class SolicitudLocalSnapshot:
    id: int
    uuid: str | None
    persona_id: int | None
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str
    updated_at: str | None

@dataclass(frozen=True)
class AccionSyncSolicitud:
    tipo: Literal["insert_local", "update_local", "insert_remoto", "update_remoto", "skip", "conflict"]
    motivo: str
    solicitud_local: Optional[SolicitudLocalSnapshot]
    fila_remota: Optional[FilaSolicitudRemota]

@dataclass(frozen=True)
class PlanSyncSolicitudes:
    acciones: list[AccionSyncSolicitud]
    conflictos: int
    omitidas: int
```

### Contratos de confirmación de solicitudes

```python
@dataclass(frozen=True)
class ItemConfirmacion:
    solicitud_id: int
    persona_id: int
    estado_objetivo: str

@dataclass(frozen=True)
class PlanConfirmacionLote:
    correlation_id: str
    items: list[ItemConfirmacion]
    generar_pdf: bool

@dataclass(frozen=True)
class ResultadoConfirmacionLote:
    confirmadas: int
    rechazadas: int
    pdf_path: str | None
    warnings: list[str]
```

### Puertos (si faltan)

```python
class SolicitudesRepositorioPuerto(Protocol):
    def obtener_por_id(self, solicitud_id: int): ...
    def guardar(self, entidad): ...
    def listar_pendientes(self): ...

class PdfServicePuerto(Protocol):
    def generar_confirmadas(self, items, destino: str | None = None) -> str: ...

class SheetsGatewayPuerto(Protocol):
    def leer_filas(self, hoja: str) -> list[dict]: ...
    def actualizar_filas(self, hoja: str, cambios: list[dict]) -> None: ...
```

---

## 5) Checklist de PRs atómicos (orden recomendado)

### PR-01 — Baseline de contratos y naming
- [ ] Crear `*_puertos.py` y `*_contratos.py` en `sync_sheets` y `solicitudes`.
- [ ] Tipar entradas/salidas de planners/runners sin tocar lógica.
- [ ] Añadir pruebas de contrato mínimas (shape/type smoke tests).

### PR-02 — Extracción de reglas puras
- [ ] Mover lógica sin IO a `*_reglas.py`.
- [ ] Mantener adaptadores de compatibilidad en archivos antiguos (delegación).
- [ ] Verificar no regresión con tests existentes.

### PR-03 — Extracción de ensambladores
- [ ] Crear `*_ensamblador.py` para DTO interno/payload.
- [ ] Eliminar mapeo ad-hoc en use cases gigantes.
- [ ] Cubrir transformaciones con tests deterministas.

### PR-04 — Extracción de planners
- [ ] Crear/ajustar `*_planner.py` para construir planes inmutables.
- [ ] El orquestador solo invoca planner y propaga plan.
- [ ] Medir reducción de LOC en `use_case.py` principales.

### PR-05 — Extracción de runners
- [ ] Crear/ajustar `*_runner.py` para ejecutar planes.
- [ ] Encapsular persistencia y side-effects detrás de puertos.
- [ ] Añadir tests de integración por runner.

### PR-06 — Auditoría/reporting desacoplado
- [ ] Mover métricas/logs a módulo de reporting/auditoría dedicado.
- [ ] Introducir eventos/resultados tipados de ejecución.
- [ ] Mantener mensajes funcionalmente equivalentes.

### PR-07 — Adelgazamiento final de fachadas
- [ ] `SheetsSyncService` y `SolicitudUseCases` quedan como coordinación.
- [ ] Cada archivo final bajo 300 LOC.
- [ ] Documentar arquitectura objetivo y mapa de responsabilidades.

---

## Resultado esperado tras el plan

- Casos de uso gigantes convertidos en orquestadores delgados.
- Responsabilidades separadas de forma explícita (reglas/planner/runner/ensamblador/puertos).
- Contratos tipados entre piezas para reducir acoplamiento y deuda futura.
- Refactor incremental, trazable y con riesgo controlado por PRs pequeños.
