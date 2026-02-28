# Plan corto de cobertura (objetivo >=85%)

## Módulos objetivo priorizados
1. `app/domain/time_utils.py`
2. `app/application/use_cases/solicitudes/use_case.py`
3. `app/infrastructure/sheets_client.py`
4. `app/infrastructure/repos_sqlite.py`

> Nota: no fue posible ejecutar `pytest --cov` en este entorno por falta del plugin `pytest-cov`; la priorización se hizo por análisis de riesgo funcional y ramas lógicas con más probabilidad de huecos.

## Funciones públicas a cubrir
- `minutes_to_hhmm`
- `SolicitudUseCases.calcular_minutos_solicitud`
- `SolicitudUseCases.calcular_saldos_por_periodo`
- `SheetsClient._with_rate_limit_retry` (contrato de resiliencia)
- `_run_with_locked_retry` y `_is_locked_operational_error` (resiliencia SQLite)

## Casos a testear (ok / error / límite)
- **`minutes_to_hhmm`**
  - OK: enteros, float, string numérica.
  - Error: `None`, string no numérica, negativos.
  - Límite: `0`, `59`, `60`, `1439`, `1440`.
- **`calcular_minutos_solicitud`**
  - OK: DTO válido.
  - Error: persona inexistente y horas negativas.
  - Límite: cálculo exacto de intervalo de 2 horas.
- **`calcular_saldos_por_periodo`**
  - OK: mes sin solicitudes y mes con solicitudes.
  - Error: fallo de repositorio (propagación).
  - Límite: saldos al borde (consumidas 0).
- **`_with_rate_limit_retry`**
  - OK: reintento con éxito en intento posterior.
  - Error: 403 -> `SheetsPermissionError`; agotamiento -> `SheetsRateLimitError`.
  - Límite: número máximo de reintentos.
- **`_run_with_locked_retry`**
  - OK: detección de lock y backoff esperado.
  - Error: lock persistente relanza `OperationalError`.
  - Límite: último intento fuera del bucle (total de invocaciones esperado).

## Qué NO se testea en este plan
- UI real (Qt/PySide).
- IO real de archivos externos salvo temporales de pytest.
- Google Sheets real / red real.
