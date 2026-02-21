# Guía de logging

## Objetivo

Definir dónde se escriben los logs operativos y cómo consultarlos para trazabilidad y soporte.

## Canales de log

- `logs/seguimiento.log`: eventos de seguimiento funcional/técnico (INFO+).
- `logs/error_operativo.log`: errores manejados pero importantes de operación (solo `ERROR`).
- `logs/crash.log`: fallos críticos/no controlados (solo `CRITICAL`).
- `logs/crashes.log`: compatibilidad legacy (mismo contenido crítico de `crash.log`).

## Diferencias de severidad

- **warning de dominio**: condiciones esperables de negocio que no rompen flujo (por ejemplo, validación rechazada o dato incompleto). Debe quedar en `WARNING` en `seguimiento.log`.
- **error_operativo**: errores técnicos controlados que requieren atención operativa pero no tiran la app.
  - Ejemplo: `database is locked`.
  - Ejemplo: `SheetsPermissionError`.
  - Destino: `error_operativo.log`.
- **crash**: excepción no controlada o fallo crítico que compromete ejecución.
  - Ejemplo: excepción no capturada en el loop principal.
  - Destino: `crash.log` (y mirror legacy en `crashes.log`).

## Formato

Los logs se consumen como **JSONL** (un objeto JSON por línea). Estructura mínima esperada:

```json
{"timestamp":"...","level":"ERROR","modulo":"...","funcion":"...","mensaje":"...","correlation_id":"..."}
```

Campos recomendados:

- `timestamp`: fecha/hora ISO.
- `level`: severidad (`INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- `correlation_id`: identificador transversal por operación.
- `extra`: contexto estructurado del evento.

## Búsqueda por `correlation_id`

```bash
rg '"correlation_id": "<ID>"' logs/seguimiento.log logs/error_operativo.log logs/crash.log
```

## Buenas prácticas

1. No registrar secretos ni datos sensibles en claro.
2. Mantener nombres de evento estables para facilitar auditoría.
3. Reutilizar el mismo `correlation_id` durante toda la operación.
4. Revisar `error_operativo.log` y `crash.log` antes de abrir bug.
