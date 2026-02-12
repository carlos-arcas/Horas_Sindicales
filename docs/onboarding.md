# Onboarding rápido (desarrollo)

Este proyecto es una app de escritorio (Python + PySide6) para gestionar horas sindicales, generar PDFs y sincronizar con Google Sheets.

Referencias útiles:
- visión global: [README.md](../README.md)
- arquitectura por capas: [arquitectura.md](../arquitectura.md)
- reglas funcionales: [reglas_negocio.md](./reglas_negocio.md)
- sincronización técnica: [sincronizacion_google_sheets.md](./sincronizacion_google_sheets.md)

## 1) Primeros 30 minutos

### Min 0–5: levantar entorno
- `pip install -r requirements.txt`
- `python main.py --selfcheck`
- `python main.py`

### Min 5–15: entender composición
Lee `main.py`: ahí está el wiring completo (DB, migraciones, repositorios, casos de uso y UI).

Mapa mental rápido:
- `app/domain`: modelo y reglas de negocio.
- `app/application`: casos de uso y orquestación.
- `app/infrastructure`: SQLite, configuración local, Google Sheets.
- `app/ui`: ventanas, diálogos y modelos Qt.

### Min 15–25: seguir un caso end-to-end
Caso recomendado: **crear solicitud**.
1. UI: `app/ui/main_window.py`.
2. Casos de uso: `app/application/use_cases.py` (`SolicitudUseCases`).
3. Dominio: `app/domain/services.py` y `app/domain/request_time.py`.
4. Persistencia: `app/infrastructure/repos_sqlite.py`.

### Min 25–30: validar
- `pytest`
- revisa tests de solicitudes, cuadrantes, sincronización y PDF en `tests/`.

## 2) Orden de lectura recomendado
1. `main.py`
2. `app/domain/models.py` + `app/domain/ports.py`
3. `app/application/use_cases.py`
4. `app/infrastructure/repos_sqlite.py` + `app/infrastructure/migrations.py`
5. `app/ui/main_window.py`

## 3) Depuración práctica
### Dónde mirar
- `logs/app.log` (ruta resuelta desde `HORAS_LOG_DIR`, `./logs` o temporal).
- `crash.log` para excepciones no controladas.
- `horas_sindicales.db` para validar estado persistido.

### Flujo recomendado
1. `python main.py --selfcheck` para descartar recursos.
2. reproducir en UI y revisar logs.
3. si es regla de negocio, cubrir con test antes de corregir.

## 4) Añadir funcionalidad sin romper capas
Checklist:
1. cambia `domain` si cambia negocio.
2. adapta `application` (DTO/casos de uso).
3. implementa en `infrastructure`.
4. actualiza migraciones si cambia esquema.
5. conecta UI.
6. añade tests.
7. ejecuta `pytest` y prueba manual básica.

Regla práctica: la UI no debe contener lógica de negocio.

## 5) Errores comunes
- Mezclar unidades de tiempo: internamente se trabaja en minutos (`*_min`).
- Saltar migraciones al añadir columnas/tablas.
- Acoplar UI a SQLite directamente.
- Cambiar puertos sin actualizar adaptadores.
- Hardcodear rutas de credenciales/logos.

## 6) Comandos rápidos
- `python main.py --selfcheck`
- `python main.py`
- `pytest`
