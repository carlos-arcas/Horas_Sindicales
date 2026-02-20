# Guía de logging

## Objetivo

Definir dónde se escriben los logs operativos y cómo consultarlos para trazabilidad y soporte.

## Archivos de log obligatorios

- `logs/seguimiento.log`: eventos de seguimiento funcional/técnico.
- `logs/crashes.log`: errores no controlados, fallos críticos y stack traces relevantes.

## Formato

Ambos logs se consumen como **JSONL** (un objeto JSON por línea). Estructura esperada mínima:

```json
{"event":"sync_started","correlation_id":"...","timestamp":"...","payload":{"...":"..."}}
```

Campos recomendados:

- `event`: nombre del evento.
- `timestamp`: fecha/hora ISO.
- `correlation_id`: identificador transversal por operación.
- `payload`: contexto estructurado del evento.

## Búsqueda por `correlation_id`

Ejemplo con `rg`:

```bash
rg '"correlation_id": "<ID>"' logs/seguimiento.log logs/crashes.log
```

Ejemplo de filtro por tipo de evento:

```bash
rg '"event": "sync_.*"' logs/seguimiento.log
```

## Buenas prácticas

1. No registrar secretos ni datos sensibles en claro.
2. Mantener nombres de evento estables para facilitar auditoría.
3. Reutilizar el mismo `correlation_id` durante toda la operación.
4. Revisar `crashes.log` en cada incidencia antes de abrir bug.

## Pendiente de completar

- Pendiente de completar política de retención/rotación por entorno (desarrollo, piloto, producción).
