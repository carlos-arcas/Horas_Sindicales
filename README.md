[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

# Horas Sindicales

Aplicación de escritorio (PySide6) para la gestión de **horas sindicales**, incluyendo:

- Alta y mantenimiento de personas.
- Registro de solicitudes de horas (por tramo o jornada completa).
- Generación de PDF de solicitudes.
- Persistencia local en SQLite con migraciones automáticas.
- Sincronización bidireccional con Google Sheets y resolución de discrepancias.

## Requisitos técnicos

- **Python 3.10 o superior** (recomendado: 3.12).
- Sistema operativo: Windows/Linux/macOS.
- Dependencias Python (ver `requirements.txt`):
  - `PySide6`
  - `reportlab`
  - `gspread`
  - `google-auth`
  - `google-auth-oauthlib`
  - `google-api-python-client`
  - `python-dotenv`

> Nota: Para usar la sincronización con Google Sheets necesitas credenciales válidas (archivo JSON de servicio/OAuth según configuración de la organización).

## Instalación

1. Clona el repositorio:

   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Horas_Sindicales
   ```

2. Crea y activa un entorno virtual:

   **Linux/macOS**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (PowerShell)**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instala dependencias:

   ```bash
   pip install -U pip
   pip install -r requirements.txt
   ```

## Ejecución

### Modo normal

```bash
python main.py
# o equivalente
python -m app
```

### Self-check (sin abrir UI)

Valida recursos estáticos básicos (por ejemplo, hoja de estilos e imágenes):

```bash
python main.py --selfcheck
# o equivalente
python -m app --selfcheck
```

### Lanzador Windows (interfaz oficial)

Para ejecutar la app con doble clic en Windows usa:

```bat
lanzar_app.bat
```

`launch.bat` se mantiene por compatibilidad, pero la interfaz oficial es `lanzar_app.bat`.

## Estructura del proyecto

```text
.
├── app/
│   ├── application/      # Casos de uso y servicios de aplicación
│   ├── domain/           # Entidades, reglas de negocio y puertos
│   ├── infrastructure/   # SQLite, migraciones, repositorios y adaptadores externos
│   ├── pdf/              # Construcción y servicio de generación de PDF
│   ├── ui/               # Ventanas, diálogos, widgets y estilos Qt
│   ├── bootstrap/        # Configuración, logging y wiring (DI)
│   └── entrypoints/      # Entrypoints CLI/UI
├── tests/                # Pruebas automatizadas (pytest)
├── main.py               # Compatibilidad: delega al entrypoint principal
├── requirements.txt      # Dependencias
└── launch.bat            # Arranque asistido en Windows
```


## Migraciones SQLite

El proyecto usa una herramienta de migración versionada basada en archivos en `migrations/`:

- `NNN_nombre.up.sql`: cambios hacia delante.
- `NNN_nombre.down.sql`: rollback del cambio.
- `NNN_nombre.up.py` (opcional): hook de transformación de datos (ej. rellenar `uuid`, migrar flags).

Se registra cada migración en la tabla `schema_migrations` (`version`, `name`, `checksum`, `applied_at`) y también se actualiza `PRAGMA user_version` con la versión aplicada.

CLI:

```bash
python -m app.infrastructure.migrations_cli status --db horas_sindicales.db
python -m app.infrastructure.migrations_cli up --db horas_sindicales.db
python -m app.infrastructure.migrations_cli down --db horas_sindicales.db --steps 1
```

## Tests

Interfaz oficial en Windows (doble clic):

```bat
ejecutar_tests.bat
```

Ejecución manual equivalente:

```bash
PYTHONPATH=. pytest -q
```

## Quality Gate

Este proyecto bloquea merges si:
- Tests fallan
- Cobertura mínima no se alcanza
- Lint detecta errores

El umbral actual de cobertura se define en `.config/quality_gate.json` (clave `coverage_fail_under`) y hoy es **63%**.
Consulta la política en `docs/coverage_policy.md`.

Comando local recomendado:
```bash
make gate
```

Para subir el umbral, crea un PR que aumente `coverage_fail_under` tras validar una cobertura total mayor en CI (redondeada hacia abajo).



## Observabilidad y Correlation ID

La aplicación incorpora trazabilidad transversal para operaciones críticas de UI y casos de uso de escritura:

- Cada operación crea un `correlation_id` único (UUID4).
- Los eventos se registran en formato estructurado homogéneo:

```json
{
  "event": "sync_started",
  "correlation_id": "...",
  "timestamp": "...",
  "payload": {"...": "..."}
}
```

Eventos típicos: `*_started`, `*_succeeded`, `*_failed` para sincronización, confirmación de lote, generación de PDF y escrituras críticas.

### Cómo seguir una operación completa en logs

1. Identifica el `correlation_id` en el primer evento (`*_started`).
2. Filtra logs por ese valor para ver toda la secuencia de eventos asociados.
3. Revisa `payload` para contexto (ids, totales, rutas de PDF, etc.).

Ejemplo de búsqueda local:

```bash
rg '"correlation_id": "<ID>"' -n .
```

## Auditoría técnica

Ver `docs/auditoria_senior.md` para el análisis completo, roadmap y scorecard.

## Cómo correr auditoría de producto

Auditoría automática (autodetección de métricas + evidencias + snapshot histórico):

```bash
python scripts/product_audit.py --auto
```

Opciones útiles:

```bash
python scripts/product_audit.py --auto --out docs/auditoria_producto.md --json-out docs/audits/latest.json
```

Esto genera `docs/auditoria_producto.md` y un snapshot versionado en `docs/audits/`.

## Documentación mínima obligatoria

La documentación mínima normalizada del proyecto está en:

- `docs/arquitectura.md`
- `docs/decisiones_tecnicas.md`
- `docs/guia_pruebas.md`
- `docs/guia_logging.md`
- `docs/definicion_producto_final.md`


## Arquitectura (resumen por capas)

El proyecto sigue una separación por capas con responsabilidades claras:

- **Domain**: modelos de negocio, reglas y contratos (puertos).
- **Application**: orquestación de casos de uso y servicios que coordinan dominio e infraestructura.
- **Infrastructure**: implementación técnica (SQLite, Google Sheets, configuración local, migraciones).
- **UI**: capa de presentación en PySide6 que consume casos de uso.

Esta organización facilita evolución, testeo y reemplazo de integraciones externas con impacto mínimo en el núcleo funcional.

## Reglas de arquitectura (imports)

Existe un test de arquitectura (`tests/test_architecture_imports.py`) que valida dependencias entre capas y falla si hay imports prohibidos.

Reglas mínimas aplicadas:
- `app/domain` no puede importar `app/application`, `app/infrastructure` ni `app/ui`.
- `app/application` no puede importar `app/ui`, `app/infrastructure` ni librerías técnicas concretas (`sqlite3`, `gspread`, `googleapiclient`).
- `app/ui` no puede importar `app/infrastructure` directamente.
- `app/infrastructure` puede depender de `domain` y `application`, pero no de `ui`.

Ejecución local:

```bash
make arch
```

## Contribución y estándares

Para contribuir siguiendo el proceso formal del proyecto, consulta:

- [Guía de contribución](CONTRIBUTING.md)
- [Definition of Done técnico](docs/definition_of_done.md)

## Licencia

Pendiente de definir. Se recomienda añadir un archivo `LICENSE` (por ejemplo, MIT, Apache-2.0 o licencia interna corporativa).
