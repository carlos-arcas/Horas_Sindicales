# API del módulo `sync`

El módulo `app.application.sync` introduce una capa de orquestación para sincronización con Google Sheets con foco en resiliencia y observabilidad.

## Objetivo

`GoogleSheetsSyncModule` envuelve `SyncSheetsUseCase` y añade:

- reintentos automáticos con exponential backoff,
- timeout configurable por ejecución,
- reporte final normalizado,
- logging estructurado en fichero JSONL,
- validación opcional de esquema antes de sincronizar,
- modo dry-run,
- cancelación cooperativa por token.

## Clases públicas

### `RetryPolicy`

```python
RetryPolicy(
    max_attempts: int = 3,
    initial_backoff_seconds: float = 0.5,
    backoff_multiplier: float = 2.0,
)
```

### `CancellationToken`

```python
token = CancellationToken()
token.cancel()          # Solicita cancelación
token.is_cancelled()    # True/False
```

### `SyncOptions`

```python
SyncOptions(
    operation: Literal["pull", "push", "sync"] = "sync",
    timeout_seconds: float = 30.0,
    dry_run: bool = False,
    check_schema: bool = True,
    retry_policy: RetryPolicy = RetryPolicy(),
    cancellation_token: CancellationToken | None = None,
)
```

### `SyncReport`

Resultado final de ejecución:

- `operation`: operación ejecutada,
- `dry_run`: indica simulación,
- `attempts`: intentos realizados,
- `creations`: altas detectadas,
- `updates`: actualizaciones detectadas,
- `omitted_duplicates`: duplicados omitidos,
- `errors`: lista de errores terminales,
- `schema_actions`: acciones de esquema aplicadas,
- `duration_seconds`: duración total.

> Nota: el reparto `creations/updates` se calcula con la señal de primera sincronización (`last_sync_at`).

### `StructuredFileLogger`

Escribe eventos de sync en formato JSON Lines (una línea JSON por evento).

```python
structured = StructuredFileLogger(Path("logs/sync.jsonl"))
structured.log("sync_started", operation="sync")
```

### `GoogleSheetsSyncModule`

```python
GoogleSheetsSyncModule(
    sync_use_case,
    schema_checker=None,
    structured_logger=None,
)
```

#### Método principal

```python
report = module.run(options)
```

## Integración recomendada

1. Crear `SyncSheetsUseCase` como en el arranque actual.
2. Inyectar `schema_checker` que llame al repositorio `ensure_schema`.
3. Configurar `StructuredFileLogger` apuntando a `logs/sync.jsonl`.
4. Ejecutar `run(SyncOptions(...))` desde UI/CLI.
