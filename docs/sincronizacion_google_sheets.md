# Sincronización con Google Sheets

> Reglas funcionales resumidas en [reglas_negocio.md](./reglas_negocio.md). Este documento cubre flujo técnico.

## 1) Visión general
La sincronización se implementa en `SheetsSyncService` y se expone vía `SyncSheetsUseCase` + `SyncSheetsAdapter`.

Operaciones:
- `pull()`: Sheets ➜ SQLite local.
- `push()`: SQLite local ➜ Sheets.
- `sync()`: `pull()` y luego `push()`.

Hojas sincronizadas: `delegadas`, `solicitudes`, `cuadrantes`, `pdf_log`, `config`.

## 2) Flujo de `push`
1. Carga configuración (`spreadsheet_id`, `credentials_path`).
2. Abre spreadsheet y asegura esquema.
3. Lee `last_sync_at` en `sync_state`.
4. Alinea cuadrantes locales desde personas.
5. Sube por entidad (`delegadas`, `solicitudes`, `cuadrantes`, `pdf_log`, `config`).
6. Actualiza `last_sync_at` (UTC ISO con `Z`).
7. Devuelve `SyncSummary` (`uploaded`, `conflicts`, `omitted_duplicates`).

Criterio de envío: solo registros con `updated_at > last_sync_at`.

## 3) Flujo de `pull`
1. Abre spreadsheet y asegura esquema.
2. Lee `last_sync_at`.
3. Descarga y procesa entidades en el mismo orden.
4. Devuelve `SyncSummary` (`downloaded`, `conflicts`, `omitted_duplicates`).

Regla por registro remoto:
- si no existe local: inserta,
- si hay conflicto: registra y omite,
- si remoto es más reciente: actualiza local,
- si no: ignora.

Nota: `pull()` no actualiza `last_sync_at`; ese sello se mueve en `push()` exitoso.

## 4) Duplicados en `solicitudes`
Clave funcional de deduplicación:
`(delegada_key, fecha_pedida, completo, minutos_total, desde_min, hasta_min)`

Detalles:
- `delegada_key`: `delegada_uuid` y fallback a `persona_id`.
- En completas, `desde/hasta` no participan.
- Horarios se normalizan antes de comparar.

Ejemplos:
- `09:00` y `9:0` se consideran equivalentes.
- Misma solicitud con UUID distinto puede omitirse si la clave funcional coincide.

## 5) Conflictos
Se detecta conflicto si ambos lados cambiaron tras `last_sync_at`:
- `local_updated_at > last_sync_at`
- `remote_updated_at > last_sync_at`

Cuando hay conflicto:
1. no se sobreescribe ninguna versión,
2. se guarda snapshot local/remoto en tabla `conflicts`,
3. se incrementa contador en `SyncSummary`.

Resolución posterior (`ConflictsService`):
- `resolve_conflict(conflict_id, keep="local"|"remote")`
- `resolve_all_latest()`

## 6) Errores y validaciones
Errores de Google (`gspread`) se traducen a errores de dominio:
- `SheetsApiDisabledError`
- `SheetsNotFoundError`
- `SheetsPermissionError`
- `SheetsCredentialsError`
- `SheetsConfigError`

Si faltan `spreadsheet_id` o `credentials_path`, se lanza `SheetsConfigError`.

Además, hay validación de placeholders SQL (`_execute_with_validation`) para detectar desajustes SQL/parámetros.

## 7) Persistencia de `last_sync_at`
- Tabla: `sync_state` (`id=1`, `last_sync_at`).
- Inicial: `NULL`.
- Actualización: solo al finalizar `push()` sin error.

Implicación: un `pull` aislado no mueve frontera temporal.

## 8) Campos sincronizados por hoja
### `delegadas`
`uuid`, `nombre`, `genero`, `activa`, `bolsa_mes_min`, `bolsa_anual_min`, `updated_at`, `source_device`, `deleted`

### `solicitudes`
`uuid`, `delegada_uuid`, `Delegada`, `fecha`, `desde_h`, `desde_m`, `hasta_h`, `hasta_m`, `completo`, `minutos_total`, `notas`, `estado`, `created_at`, `updated_at`, `source_device`, `deleted`, `pdf_id`

### `cuadrantes`
`uuid`, `delegada_uuid`, `dia_semana`, `man_h`, `man_m`, `tar_h`, `tar_m`, `updated_at`, `source_device`, `deleted`

### `pdf_log`
`pdf_id`, `delegada_uuid`, `rango_fechas`, `fecha_generacion`, `hash`, `updated_at`, `source_device`

### `config`
`key`, `value`, `updated_at`, `source_device`

## 9) Riesgos operativos principales
- API/credenciales Google inválidas.
- Edición manual de columnas clave en Sheets.
- Timestamps inválidos o no parseables.
- Cambios parciales (sin transacción global de todo `pull/push`).
- Conflictos acumulados sin resolver.
