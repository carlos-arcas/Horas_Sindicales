[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

# Horas Sindicales

Aplicación de escritorio (PySide6) para gestionar horas sindicales, solicitudes y sincronización con Google Sheets, con arquitectura en capas y quality gate reproducible.

## Qué problema resuelve

En muchos equipos sindicales, el seguimiento de horas, solicitudes y justificantes PDF se hace con hojas dispersas y procesos manuales. Este proyecto centraliza el flujo para:

- Registrar personas y solicitudes de horas.
- Generar PDF de solicitudes con trazabilidad.
- Persistir datos localmente en SQLite.
- Sincronizar con Google Sheets con manejo de conflictos.

## Arquitectura

Regla principal de dependencias:

```text
UI -> Casos de uso -> Puertos -> Infraestructura
```

Diagrama ASCII simplificado:

```text
app/ui (PySide6)
    |
    v
app/application (casos de uso)
    |
    v
app/domain (reglas y contratos)
    |
    v
app/infrastructure (sqlite, sheets, adapters)
```

Principios aplicados:

- Sin lógica de negocio en UI.
- Casos de uso en `app/application`.
- Reglas de negocio en `app/domain`.
- Implementaciones técnicas en `app/infrastructure`.

## Cómo ejecutar

### Windows (doble clic)

Scripts oficiales del repositorio:

```bat
lanzar_app.bat
launcher.bat
```

### CLI

```bash
python main.py
# o
python -m app
```

## Testing y calidad

### Windows (doble clic)

```bat
ejecutar_tests.bat
menu_validacion.bat
quality_gate.bat
```

### CLI

```bash
python -m pip install -r requirements-dev.txt
python scripts/quality_gate.py
```

El gate CORE toma el umbral desde `.config/quality_gate.json`.

- Umbral actual (fase 1): **80%**.
- Objetivo contractual final: **85%**.
- Roadmap de escalado: **80% → 83% → 85%**.

Referencia de contrato de cobertura: `docs/coverage_policy.md`.

## Observabilidad

El proyecto registra eventos con `correlation_id` para seguir operaciones end-to-end en logs.

- `correlation_id`: disponible y operativo.
- `incident_id`: **pendiente (roadmap)**; se incorporará en la capa de observabilidad (`app/core/observability.py`) y en el manejo global de excepciones (`app/bootstrap/exception_handler.py`).

Búsqueda útil en logs:

```bash
rg 'correlation_id' -n logs app
```

## Roadmap (corto)

1. Cobertura CORE 80% (setup y contrato).
2. Subir a 83% con nuevos tests de dominio/aplicación.
3. Alcanzar 85% contractual en CORE.
4. Añadir `incident_id` en trazas de error y correlación con reportes de soporte.
5. Endurecer smoke UI y auditoría E2E en CI.
