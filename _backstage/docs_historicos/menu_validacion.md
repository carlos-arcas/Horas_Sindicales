# Menú de validación (`menu_validacion.bat`)

`menu_validacion.bat` es un menú operativo para ejecutar validaciones del proyecto sin duplicar lógica de entornos virtuales. El menú delega en scripts existentes:

- `ejecutar_tests.bat`
- `quality_gate.bat`

## Opciones del menú

1. **Ejecutar tests**
   - Llama a `ejecutar_tests.bat`.
   - Guarda stdout en `logs\menu_tests_stdout.txt`.
   - Guarda stderr en `logs\menu_tests_stderr.txt`.

2. **Ejecutar quality gate**
   - Llama a `quality_gate.bat`.
   - Guarda stdout en `logs\menu_gate_stdout.txt`.
   - Guarda stderr en `logs\menu_gate_stderr.txt`.

3. **Ejecutar ambos en orden**
   - Ejecuta primero `ejecutar_tests.bat`.
   - Si tests falla, corta el flujo y **no** ejecuta `quality_gate.bat` (fallo temprano).
   - Si tests pasa, ejecuta `quality_gate.bat`.

4. **Abrir carpeta logs**
   - Abre la carpeta `logs\` para consultar resultados.

0. **Salir**
   - Cierra el menú.

## Ubicación de logs

El menú crea `logs\` si no existe y escribe siempre:

- `logs\menu_ultima_ejecucion.txt` (resumen + salida consolidada)

Además, mantiene archivos separados por script:

- `logs\menu_tests_stdout.txt`
- `logs\menu_tests_stderr.txt`
- `logs\menu_gate_stdout.txt`
- `logs\menu_gate_stderr.txt`

## Cómo compartir resultados

Para compartir una ejecución:

1. Abre `logs\menu_ultima_ejecucion.txt`.
2. Copia y pega todo el contenido en el canal de soporte o ticket.

Ese archivo incluye:

- estado de tests y quality gate
- códigos de salida
- salida capturada de stdout/stderr por ejecución
