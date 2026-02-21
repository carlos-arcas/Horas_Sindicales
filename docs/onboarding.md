# Onboarding rápido (developer)

Este proyecto es una app de escritorio en **Python + PySide6** para gestionar horas sindicales, generar PDFs y sincronizar con Google Sheets.

## 1) Cómo entender el proyecto en 30 minutos

### Min 0–5: arranca y valida entorno
- Instala dependencias: `pip install -r requirements.txt`.
- Ejecuta check de recursos (sin abrir UI): `python main.py --selfcheck`.
- Si pasa, abre la app: `python main.py`.

### Min 5–15: entiende el flujo principal
- Lee `main.py` para ver el wiring completo: DB, migraciones, repos, servicios, casos de uso y UI.
- Identifica capas:
  - `app/domain`: modelos + reglas de negocio puras.
  - `app/application`: casos de uso y DTOs.
  - `app/infrastructure`: SQLite, config local y Google Sheets.
  - `app/ui`: ventanas, diálogos y modelos Qt.

### Min 15–25: recorre un caso real end-to-end
Caso recomendado: **crear solicitud**.
1. UI: `app/ui/main_window.py` (acciones/botones).
2. App: `app/application/use_cases.py` (`SolicitudUseCases`).
3. Dominio: validaciones en `app/domain/services.py` y cálculo en `app/domain/request_time.py`.
4. Infra: persistencia en `app/infrastructure/repos_sqlite.py`.

### Min 25–30: confirma expectativas con tests
- Ejecuta `pytest`.
- Revisa especialmente tests de solicitudes, cuadrantes y PDF en `tests/`.

---

## 2) Por dónde empezar a leer código
Orden recomendado:
1. `main.py` (bootstrap y dependencias).
2. `app/domain/models.py` y `app/domain/ports.py` (lenguaje del negocio + contratos).
3. `app/application/use_cases.py` (orquestación real).
4. `app/infrastructure/repos_sqlite.py` + `app/infrastructure/migrations.py` (cómo persiste datos).
5. `app/ui/main_window.py` (cómo se dispara todo desde la UI).

Si vienes de backend, empieza por domain/application. Si vienes de frontend desktop, empieza por UI y sigue hacia casos de uso.

---

## 3) Archivos clave
- **Entrada y ciclo de vida**: `main.py`.
- **Reglas de negocio**: `app/domain/services.py`, `app/domain/request_time.py`.
- **Modelos base**: `app/domain/models.py`.
- **Puertos (arquitectura)**: `app/domain/ports.py`.
- **Casos de uso**: `app/application/use_cases.py`.
- **Persistencia SQLite**: `app/infrastructure/repos_sqlite.py`.
- **Migraciones DB**: `app/infrastructure/migrations.py`.
- **Ventana principal**: `app/ui/main_window.py`.
- **Generación PDF**: `app/pdf/pdf_builder.py` y `app/pdf/service.py`.
- **Sync con Sheets**: `app/application/sync_sheets_use_case.py`, `app/infrastructure/sync_sheets_adapter.py`.

---

## 4) Cómo depurar (práctico)

Referencia rápida de persistencia local: `docs/db_runtime.md`.


### Logs
- La app escribe logs en `app.log` dentro de `HORAS_LOG_DIR`, `./logs` o temp (fallback definido en `main.py`).
- Crashes no controlados van a `crash.log`.

### Estrategia recomendada
1. Reproducir con `python main.py --selfcheck` para aislar errores de recursos.
2. Reproducir en UI (`python main.py`) y mirar `logs/app.log`.
3. Si el problema es de datos, inspeccionar `horas_sindicales.db` en la carpeta runtime (`%LOCALAPPDATA%\HorasSindicales\data` o `~/.local/share/HorasSindicales/data`).
4. Si el problema es de reglas, escribir/ajustar test primero en `tests/`.

### Casos típicos
- Error al sincronizar: revisar config local y credenciales en `~/.local/share/HorasSindicales` (o `%LOCALAPPDATA%\HorasSindicales`).
- Error de PDF: validar rutas/logo y campos usados por `pdf_builder.py`.

---

## 5) Cómo añadir una nueva funcionalidad

Checklist corto:
1. Define regla/modelo en `domain` (si cambia negocio).
2. Extiende DTO/caso de uso en `application`.
3. Añade/ajusta persistencia en `infrastructure`.
4. Si hay cambio de esquema, actualiza `run_migrations`.
5. Conecta evento/estado en `ui`.
6. Añade tests de unidad y de integración mínima.
7. Ejecuta `pytest` + prueba manual en UI.

Regla práctica: evita meter lógica de negocio en la UI; la UI debe delegar en casos de uso.

---

## 6) Errores comunes a evitar
- **Mezclar horas y minutos**: en dominio y DB se trabaja en minutos (`*_min`).
- **Saltarte migraciones** al añadir columnas/tablas.
- **Acoplar UI con SQLite directamente** en vez de usar casos de uso/repositorios.
- **No cubrir validaciones con tests** (fechas, duplicados, jornadas completas/parciales).
- **Modificar contrato de puertos** sin actualizar adaptadores e implementación.
- **Hardcodear rutas locales** para credenciales/logos.

---

## Comandos útiles
- `python main.py --selfcheck`
- `python main.py`
- `pytest`
