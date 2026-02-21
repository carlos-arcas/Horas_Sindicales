# Guía de logging

## Objetivo

Definir canales separados para seguimiento, error operativo y crash real sin mezclar señales.

## Archivos de log

- `logs/seguimiento.log`: trazas funcionales/técnicas (INFO+).
- `logs/error_operativo.log`: **solo `ERROR` manejados** (ej. sync, IO, `database is locked`, permisos de Sheets).
- `logs/crash.log`: **solo `CRITICAL` y excepciones no controladas**.
- Compatibilidad legacy: se mantiene `logs/crashes.log` para instalaciones/scripts previos.

## Política de severidad

- **warning de dominio**: anomalía esperable de negocio, no bloqueante.
- **error_operativo (`ERROR`)**: fallo manejado pero relevante para operación/soporte.
- **crash (`CRITICAL`)**: excepción no controlada o estado irrecuperable.

> Política elegida: `CRITICAL` **no** entra en `error_operativo.log` para evitar duplicidad y mantener señales limpias.

## Ejemplos

- `database is locked` → `error_operativo.log`
- `SheetsPermissionError` → `error_operativo.log`
- excepción no controlada en runtime/UI/CLI → `crash.log`

## Formato

Los archivos se emiten como JSONL con campos estructurados (timestamp, módulo, función, mensaje, `correlation_id`, `result_id` cuando aplica, y `exc_info` si hay excepción).

## Búsqueda por `correlation_id`

```bash
rg '"correlation_id": "<ID>"' logs/seguimiento.log logs/error_operativo.log logs/crash.log
```

## Buenas prácticas

1. No registrar secretos.
2. Mantener `correlation_id` en toda la operación.
3. Para errores manejados, usar helper de bootstrap `log_operational_error(...)`.
4. Ante incidencias graves, revisar primero `crash.log`.
