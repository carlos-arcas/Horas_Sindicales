# Guía de pruebas

## Quality gate de tamaño y complejidad

La suite incluye `tests/test_quality_gate_metrics.py`, que valida dos métricas sobre `app/`:

- **LOC por archivo** (líneas de código sin comentarios/blancos) con umbral `MAX_LOC_POR_ARCHIVO`.
- **Complejidad ciclomática por función/método** con umbral `MAX_CC_POR_FUNCION`.

La configuración vive en `app/configuracion/calidad.py`.

### Cómo ajustar umbrales

1. Edita `MAX_LOC_POR_ARCHIVO` y/o `MAX_CC_POR_FUNCION`.
2. Ejecuta `pytest -q` (o `ejecutar_tests.bat` en Windows) para validar el impacto.

### Excepciones baseline (deuda técnica)

Se permiten excepciones controladas en:

- `EXCEPCIONES_LOC`
- `EXCEPCIONES_CC`

Estas excepciones **no deben crecer**: cualquier aumento falla el test.
Añadir una excepción nueva debe ser la última opción y requiere justificar por qué no se pudo refactorizar/extraer responsabilidades.
