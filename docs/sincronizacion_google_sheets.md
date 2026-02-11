# Sincronización con Google Sheets (documentación técnica)

## 1) Visión general

La sincronización está implementada en `SheetsSyncService` y se expone por `SyncSheetsUseCase`/`SyncSheetsAdapter`.

- `pull()`: trae cambios desde Sheets a SQLite local.
- `push()`: sube cambios locales a Sheets.
- `sync()`: ejecuta `pull()` y luego `push()` (en ese orden).

El servicio trabaja sobre cinco hojas: `delegadas`, `solicitudes`, `cuadrantes`, `pdf_log` y `config`.

---

## 2) Flujo de **push** (local ➜ Google Sheets)

### Secuencia de alto nivel

1. Carga configuración de Sheets (`spreadsheet_id`, `credentials_path`).
2. Abre el spreadsheet con cuenta de servicio.
3. Asegura esquema mínimo (hojas + cabeceras requeridas).
4. Lee `last_sync_at` desde `sync_state`.
5. Sincroniza primero `cuadrantes` locales derivados de `personas` (`_sync_local_cuadrantes_from_personas`).
6. Ejecuta push por entidad:
   - `delegadas`
   - `solicitudes`
   - `cuadrantes`
   - `pdf_log`
   - `config`
7. Actualiza `last_sync_at` al timestamp UTC actual (ISO con `Z`).
8. Devuelve `SyncSummary` con `uploaded`, `conflicts`, `omitted_duplicates`.

### Regla para decidir qué subir

Solo se consideran filas locales con `updated_at > last_sync_at` (`_is_after_last_sync`). Si no hay `last_sync_at`, se considera “primera sincronización” y se evalúan todas las filas con `updated_at` no nulo.

### Regla de actualización remota

Para cada fila local:

- Si existe en Sheets por `uuid` (o por PK en tablas auxiliares): se actualiza su fila (`worksheet.update(...)`).
- Si no existe: se inserta (`append_row(...)`).
- Si hay conflicto temporal bidireccional (ver sección 5), no se sube; se registra en `conflicts`.

---

## 3) Flujo de **pull** (Google Sheets ➜ local)

### Secuencia de alto nivel

1. Abre spreadsheet y asegura esquema.
2. Lee `last_sync_at`.
3. Descarga y procesa en orden:
   - `delegadas`
   - `solicitudes`
   - `cuadrantes`
   - `pdf_log`
   - `config`
4. Devuelve `SyncSummary` con `downloaded`, `conflicts`, `omitted_duplicates`.

> Importante: `pull()` **no actualiza** `last_sync_at`. El sellado de sincronización ocurre en `push()`.

### Regla por fila remota

Para cada registro remoto:

- Si no existe localmente: se inserta.
- Si existe y hay conflicto: se registra en `conflicts` y se omite aplicar cambio.
- Si existe y remoto es más nuevo (`remote.updated_at > local.updated_at`): se actualiza local.
- Si remoto no es más nuevo: se ignora.

En `config`, además de persistir en `sync_config`, se aplica side effect para `key=pdf_text` actualizando `grupo_config.pdf_intro_text`.

---

## 4) Detección de duplicados

La deduplicación está implementada solo para `solicitudes`.

## Clave de deduplicación

Se construye una tupla lógica:

`(delegada_key, fecha_pedida, completo, minutos_total, desde_min, hasta_min)`

Donde:

- `delegada_key` prioriza `delegada_uuid`; fallback `persona_id`.
- Si `completo = true`, el rango horario no se usa (`desde/hasta = None`) para comparar.
- Horas y minutos se normalizan para evitar falsos negativos (p. ej. `09:00` vs `9` + `0`).

### En pull

Si llega una `solicitud` remota sin equivalente por `uuid`, se calcula clave dedupe y se consulta si ya existe una solicitud local activa con misma clave. Si existe, se omite inserción y se incrementa `omitted_duplicates`.

### En push

Si una `solicitud` local no existe en remoto por `uuid`, se compara su clave dedupe contra un índice de solicitudes remotas. Si la clave ya existe en remoto, se omite upload y se incrementa `omitted_duplicates`.

---

## 5) Manejo de errores

## Errores de configuración/credenciales/API

`SheetsClient.open_spreadsheet()` captura excepciones de `gspread` y las traduce mediante `map_gspread_exception(...)` a errores de dominio:

- `SheetsApiDisabledError`: API no habilitada en GCP.
- `SheetsNotFoundError`: spreadsheet inexistente/ID inválido.
- `SheetsPermissionError`: falta de permisos (hoja no compartida con service account).
- `SheetsCredentialsError`: JSON inexistente o inválido.
- `SheetsConfigError`: fallback para otros errores.

Además, si falta configuración (`spreadsheet_id` o `credentials_path`), se lanza `SheetsConfigError` al abrir spreadsheet.

## Errores internos de SQL

Existe validación explícita de placeholders (`_execute_with_validation`) para prevenir desajustes entre SQL y parámetros; en error lanza `ValueError`.

## Comportamiento transaccional

La implementación hace `commit()` por bloques y por operaciones (según método). No hay transacción global de todo `pull/push`; por tanto, pueden persistir cambios parciales si una operación posterior falla.

---

## 6) Conflictos: qué ocurre

## Detección

Se considera conflicto si **ambos lados** cambiaron después de `last_sync_at`:

- `local_updated_at > last_sync_at`
- `remote_updated_at > last_sync_at`

Si falta cualquiera de los timestamps, no se marca conflicto.

## Efecto inmediato durante sync

Cuando se detecta conflicto:

1. No se aplica actualización ni push para ese registro.
2. Se inserta una fila en `conflicts` con snapshots JSON (`local_snapshot_json`, `remote_snapshot_json`) y `detected_at`.
3. Se incrementa el contador `conflicts` del `SyncSummary`.

## Resolución posterior

`ConflictsService` permite:

- `resolve_conflict(conflict_id, keep="local"|"remote")`.
- `resolve_all_latest()`: resuelve en lote eligiendo automáticamente snapshot más reciente.

Al resolver:

- Si se elige `local`, se reescribe local y se marca “dirty” (`updated_at=now`, `source_device=device_id`) para que salga en próximo `push`.
- Si se elige `remote`, se aplica snapshot remoto en local sin marcar dirty adicional.
- Luego se elimina registro de `conflicts`.

---

## 7) Datos enviados (campos por hoja)

Estos son los campos de payload definidos por esquema (`SHEETS_SCHEMA`) y usados en push/pull.

## `delegadas`

- `uuid`
- `nombre`
- `genero`
- `activa`
- `bolsa_mes_min`
- `bolsa_anual_min`
- `updated_at`
- `source_device`
- `deleted`

## `solicitudes`

- `uuid`
- `delegada_uuid`
- `Delegada`
- `fecha`
- `desde_h`
- `desde_m`
- `hasta_h`
- `hasta_m`
- `completo`
- `minutos_total`
- `notas`
- `estado`
- `created_at`
- `updated_at`
- `source_device`
- `deleted`
- `pdf_id`

## `cuadrantes`

- `uuid`
- `delegada_uuid`
- `dia_semana`
- `man_h`
- `man_m`
- `tar_h`
- `tar_m`
- `updated_at`
- `source_device`
- `deleted`

## `pdf_log`

- `pdf_id`
- `delegada_uuid`
- `rango_fechas`
- `fecha_generacion`
- `hash`
- `updated_at`
- `source_device`

## `config`

- `key`
- `value`
- `updated_at`
- `source_device`

---

## 8) Persistencia de `last_sync_at`

- Se guarda en tabla SQLite `sync_state` (fila única `id=1`, columna `last_sync_at`).
- Se inicializa en migraciones con `NULL`.
- Se actualiza **solo** al finalizar `push()` exitosamente, usando `now()` UTC en ISO 8601 con sufijo `Z`.

Implicaciones:

- Un `pull()` aislado no mueve frontera temporal.
- `sync()` sí la mueve porque termina con `push()`.

---

## 9) Posibles puntos de fallo (operativos y de mantenimiento)

1. **Conectividad/API Google**
   - API deshabilitada, rate limits, latencia o errores 403/404.
2. **Credenciales**
   - JSON ausente/dañado o service account sin compartir en el spreadsheet.
3. **Inconsistencias de esquema en hoja**
   - Columnas cambiadas manualmente; el sistema añade faltantes, pero no corrige renombrados inválidos.
4. **Timestamps inválidos**
   - Si `updated_at` no parsea ISO, la lógica temporal puede omitir sync/conflictos.
5. **Cambios parciales por falta de transacción global**
   - Fallo a mitad de push/pull puede dejar estado intermedio.
6. **Conflictos no resueltos**
   - Si se acumulan en `conflicts`, pueden “congelar” propagación de ciertos registros.
7. **Dependencia de UUIDs y referencias**
   - Si llega `solicitud` remota con `delegada_uuid` inexistente local, no se inserta.
8. **Dedupe conservador en solicitudes**
   - Puede omitir inserción si clave lógica coincide aunque `uuid` sea distinto (esperado por diseño, pero relevante para auditoría).
9. **Contención por edición manual en Sheets**
   - Modificaciones manuales frecuentes elevan tasa de conflicto y necesidad de resolución.

---

## 10) Recomendaciones de mantenimiento

- Mantener `updated_at` en formato ISO UTC consistente (`...Z`).
- Evitar editar columnas clave (`uuid`, `updated_at`, `delegada_uuid`) manualmente en Sheets.
- Revisar periódicamente tabla `conflicts` y resolver en UI/servicio.
- Si se añade una nueva entidad sincronizable:
  1. Definir hoja+columnas en `SHEETS_SCHEMA`.
  2. Añadir pull/push simétricos.
  3. Definir criterio de conflicto y dedupe (si aplica).
  4. Añadir tests de regresión para conflicto/dedupe/timestamps.

