# Arquitectura del proyecto `Horas_Sindicales`

## 1) Diagrama conceptual (texto)

```text
┌──────────────────────────────────────────────────────────────┐
│                           UI                                │
│  app/ui/* (PySide6): ventanas, diálogos, modelos Qt         │
└───────────────┬──────────────────────────────────────────────┘
                │ usa
┌───────────────▼──────────────────────────────────────────────┐
│                        Application                           │
│ app/application/*: casos de uso, DTOs, servicios de orquest.│
│ app/pdf/*: generación de PDF invocada desde casos de uso     │
└───────────────┬──────────────────────────────────────────────┘
                │ depende de puertos y modelos
┌───────────────▼──────────────────────────────────────────────┐
│                          Domain                              │
│ app/domain/*: entidades, reglas, utilidades de negocio,      │
│ puertos (Protocol) y errores de dominio                      │
└───────────────┬──────────────────────────────────────────────┘
                │ implementado por
┌───────────────▼──────────────────────────────────────────────┐
│                      Infrastructure                          │
│ app/infrastructure/*: SQLite, migraciones, repos concretos,  │
│ cliente/adaptadores Google Sheets, config local              │
└──────────────────────────────────────────────────────────────┘

Composición de dependencias:
main.py → instancia infraestructura concreta → inyecta en application/ui.
```

> Nota técnica honesta: el proyecto sigue una separación por capas bastante clara, pero **no es una Clean Architecture estricta**. Hay acoplamientos pragmáticos (por ejemplo, servicios de aplicación que conocen `sqlite3.Connection`, y un módulo `app/pdf` fuera de las 4 capas clásicas) que lo vuelven una arquitectura híbrida y práctica.

---

## 2) Explicación de cada capa

### Domain (`app/domain`)

Responsabilidad:
- Modelar el núcleo del negocio y sus reglas básicas.
- Definir contratos (puertos) que otras capas deben implementar.

Elementos observables:
- Entidades inmutables con `@dataclass(frozen=True)` como `Persona`, `Solicitud`, `GrupoConfig`, `SheetsConfig`. 
- Validaciones de negocio (`validar_persona`, `validar_solicitud`, `validar_sheets_config`) y excepciones semánticas (`ValidacionError`, `BusinessRuleError`).
- Puertos en forma de `Protocol` para repositorios y servicios externos (`PersonaRepository`, `SolicitudRepository`, `SheetsGatewayPort`, `SheetsSyncPort`, etc.).

Lectura arquitectónica:
- El dominio no depende de PySide, SQLite ni gspread.
- Expone contratos que permiten desacoplar la persistencia/sincronización de la lógica de negocio.

### Application (`app/application`)

Responsabilidad:
- Orquestar casos de uso.
- Convertir entre DTOs y entidades.
- Aplicar reglas de negocio usando dominio + puertos.

Elementos observables:
- `PersonaUseCases`, `SolicitudUseCases`, `GrupoConfigUseCases` centralizan operaciones funcionales (alta/edición/listado/cálculos/generación PDF).
- `SyncSheetsUseCase` delega en el puerto `SheetsSyncPort`.
- `SheetsService` gestiona configuración de Google Sheets, normalización de ID y prueba de conexión con esquema.

Lectura arquitectónica:
- Esta capa está relativamente bien separada, aunque no completamente “pura”: `ConflictsService` (ubicado en `application`) trabaja directamente con SQL y conexión SQLite, lo cual es una concesión práctica que mezcla responsabilidades de aplicación+infraestructura.

### Infrastructure (`app/infrastructure`)

Responsabilidad:
- Implementar acceso a datos y a servicios externos.

Elementos observables:
- SQLite:
  - conexión (`db.py`),
  - migraciones (`migrations.py`),
  - seed inicial (`seed.py`),
  - repositorios concretos (`repos_sqlite.py`).
- Google Sheets:
  - cliente gspread (`sheets_client.py`),
  - gestión de estructura de hojas (`sheets_repository.py`),
  - gateway para prueba de conexión (`sheets_gateway_gspread.py`),
  - sincronización local↔remota (`sheets_sync_service.py`, `sync_sheets_adapter.py`).
- Configuración local de credenciales y `device_id` (`local_config.py`, `local_config_store.py`).

Lectura arquitectónica:
- Es la capa más “operativa” y concentra detalles técnicos concretos.
- Implementa puertos definidos en dominio y consumidos por aplicación.

### UI (`app/ui`)

Responsabilidad:
- Interacción con usuario y renderizado.

Elementos observables:
- `MainWindow` y diálogos (`person_dialog`, `group_dialog`, `dialog_opciones`, etc.) para operaciones funcionales.
- Modelos Qt (`models_qt.py`) y estilo visual (`style.py`, `styles/*.qss`).
- Invoca casos de uso/servicios de aplicación inyectados desde `main.py`.

Lectura arquitectónica:
- La UI no crea repositorios ni conexiones; recibe dependencias ya construidas.
- Maneja asincronía de UI (hilos Qt) para sincronización sin bloquear interfaz.

---

## 3) Regla de dependencias (Dependency Rule)

Regla observada en el proyecto (aproximada):
- UI → Application → Domain.
- Infrastructure implementa contratos hacia adentro (Domain/Application) y `main.py` hace el “wiring”.

Qué sí se cumple:
- Los puertos están definidos en `domain` y se implementan en `infrastructure`.
- Los casos de uso usan abstracciones (puertos), no clases concretas de gspread/SQLite en la mayoría de flujos.

Qué no es estrictamente limpio:
- Existen componentes de aplicación con dependencia directa en `sqlite3` (`ConflictsService`).
- El paquete `app/pdf` no está claramente dentro del esquema de 4 capas y se invoca desde application.

Conclusión:
- Hay una **arquitectura por capas con puertos/adaptadores parcial**, pero no una implementación canónica rígida de Clean Architecture.

---

## 4) Inyección de dependencias

La inyección es **manual por composición en `main.py`**:

1. Se crea conexión SQLite y se ejecutan migraciones/seed.
2. Se instancian repositorios concretos SQLite.
3. Se construyen servicios/casos de uso de aplicación con esos repositorios.
4. Se montan adaptadores de Google Sheets.
5. Se inyecta todo en `MainWindow`.

Patrón utilizado:
- Composition Root en `main._run_app()`.
- Constructor injection (parámetros en `__init__`) tanto en application como en UI.

No hay contenedor DI (tipo `injector`, `dependency-injector`, etc.); la resolución es explícita y trazable.

---

## 5) Manejo de SQLite y Google Sheets

### SQLite

- Motor principal de persistencia local.
- Archivo `horas_sindicales.db` en raíz del proyecto por defecto.
- Conexión vía `sqlite3.connect`, con `row_factory=sqlite3.Row`.
- Migraciones imperativas al arranque (`run_migrations`) para crear/ajustar tablas y columnas.
- Repositorios SQLite encapsulan CRUD y conversión fila→entidad.
- También se almacenan tablas de sincronización (`sync_state`, `conflicts`, `sync_config`, `pdf_log`, etc.).

Implicación:
- Modelo “offline-first” local con sincronización posterior hacia Google Sheets.

### Google Sheets

- Integración mediante `gspread` y cuenta de servicio JSON.
- `SheetsService` valida/normaliza configuración y prueba conexión.
- `SheetsRepository` garantiza esquema de hojas/cabeceras (`SHEETS_SCHEMA`).
- `SheetsSyncService` realiza `pull`, `push` y `sync`, comparando timestamps, gestionando conflictos y evitando duplicados.
- `SyncSheetsAdapter` abre/cierra conexión SQLite por operación de sincronización y delega al servicio de sync.

Implicación:
- Google Sheets funciona como backend compartido/sincronizable, no como fuente única inmediata.

---

## 6) Gestión de hilos

Sí, existen hilos en la capa UI:

- `MainWindow` crea `QThread` para ejecutar procesos de sincronización (`sync` y `push`) en segundo plano.
- Se usan `QObject` workers (`SyncWorker`, `PushWorker`) con señales:
  - `finished(SyncSummary)`
  - `failed(object)`
- Flujo típico:
  1. mover worker al hilo (`moveToThread`),
  2. conectar `thread.started -> worker.run`,
  3. conectar `finished/failed` a callbacks de UI,
  4. liberar recursos (`quit`, `deleteLater`).

Objetivo:
- Evitar bloquear el hilo principal de Qt durante operaciones I/O (red + sincronización).

No se observa uso de `asyncio` ni thread pool genérico; la estrategia es la estándar de Qt con `QThread` + signals/slots.

---

## 7) Posibles mejoras futuras (realistas)

1. **Separar `ConflictsService` en puerto + adapter de infraestructura**
   - Beneficio: dependencia más limpia de application respecto a SQLite.

2. **Centralizar casos de uso de sincronización**
   - `SheetsSyncService` es extenso; podría dividirse en subcomponentes por agregado (`delegadas`, `solicitudes`, `cuadrantes`, `config`, `pdf_log`) para legibilidad y testabilidad.

3. **Formalizar el módulo PDF dentro de capas**
   - Definirlo explícitamente como infraestructura/document service o como adapter de salida.

4. **Estrategia transaccional más explícita**
   - Agrupar commits por unidad funcional crítica en sync para facilitar rollback lógico y auditoría.

5. **Observabilidad de sync**
   - Añadir métricas estructuradas (tiempos por fase, número de operaciones remotas/locales, tasa de conflictos).

6. **Documentar decisiones arquitectónicas (ADR)**
   - Registrar por qué se eligió SQLite + Sheets y los trade-offs de consistencia eventual.

7. **Tests de integración de arquitectura**
   - Casos end-to-end con base temporal y mocks de gspread para validar flujos `push/pull/sync` completos.

---

## Resumen ejecutivo

El sistema está organizado en capas con separación razonable entre UI, aplicación, dominio e infraestructura, y usa puertos/adaptadores en varias zonas clave (repositorios y sincronización). Aun así, mantiene decisiones pragmáticas que rompen la pureza de Clean Architecture estricta (acoplamientos puntuales a SQLite y módulo PDF transversal). Técnicamente, la arquitectura es **híbrida, mantenible y orientada a producto desktop offline-first con sincronización a Google Sheets**.
