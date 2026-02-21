# Base de datos SQLite local

## Política de versionado

La base de datos local **no debe versionarse** en Git porque contiene datos de ejecución de cada equipo y cambia continuamente.
Por esta razón, el repositorio ignora explícitamente `horas_sindicales.db` y en general cualquier `*.db`, `*.sqlite` y derivados (`*.db-wal`, `*.db-shm`, `*.db-journal`).

## Ubicación local

Por defecto, la aplicación crea y usa la base de datos en:

- `logs/runtime/horas_sindicales.db`

Esta ruta vive en infraestructura (no en dominio), manteniendo Clean Architecture.

## Cómo regenerarla

Si falta el archivo de DB, la aplicación lo vuelve a crear automáticamente al iniciar.
Además, durante el arranque:

1. Se ejecutan migraciones (`run_migrations`).
2. Se aplica seed inicial si procede (`seed_if_empty`).

También puedes gestionarla manualmente con la CLI de migraciones, por ejemplo:

```bash
python -m app.infrastructure.migrations_cli up --db logs/runtime/horas_sindicales.db
```
