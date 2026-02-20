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

## Tests UI (PySide6)

La suite separa los tests de interfaz bajo `tests/ui/` y los marca automáticamente con `@pytest.mark.ui` desde `tests/conftest.py`.

### Ejecución recomendada

- Ejecutar toda la suite: `pytest -q`
- Ejecutar solo UI: `pytest -m ui`

### Estabilidad en entornos headless

En Linux sin servidor gráfico (`DISPLAY` y `WAYLAND_DISPLAY` ausentes), la configuración de tests fuerza:

- `QT_QPA_PLATFORM=offscreen`
- `QT_OPENGL=software`

Si PySide6/Qt no puede cargarse igualmente (por ejemplo, por `libGL.so.1`), los tests marcados como `ui` se omiten automáticamente con un motivo explícito, sin romper la colección ni el pipeline.

### Requisitos mínimos locales

- **Windows**
  - Instalar dependencias del proyecto (`requirements-dev.txt`).
  - Ejecutar `pytest -m ui` en una sesión normal de escritorio.

- **Linux**
  - Instalar dependencias del proyecto (`requirements-dev.txt`).
  - Tener soporte gráfico/GL disponible para tests UI completos.
  - Si aparece error por `libGL.so.1`, instalar los paquetes de OpenGL/Mesa típicos de la distro (por ejemplo `libgl1` en Debian/Ubuntu) y reintentar.
