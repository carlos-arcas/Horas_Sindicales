# Convenciones oficiales de naming

## Objetivo
Este documento define la convención oficial de nombres para mantener consistencia en nuevas contribuciones, sin exigir un renombrado masivo del histórico del repositorio.

## 1) Idioma preferido
- **Idioma principal: español** para nombres de módulos, funciones, clases de dominio, carpetas y scripts internos.
- **Excepciones permitidas**:
  - Nombres obligatorios o convencionales del framework/librerías (`__init__.py`, `conftest.py`, `pytest`, `tkinter`, etc.).
  - Clases o componentes UI con nombres ampliamente establecidos por la tecnología.
  - Términos técnicos difíciles de traducir sin perder precisión (`hash`, `cache`, `token`, `payload`, etc.).

## 2) Estilo de nombres
- **Archivos Python y funciones**: `snake_case`.
  - Regla mínima para nuevos archivos en `app/`: `[a-z0-9_]+\.py`.
  - Nunca usar espacios ni mayúsculas en nombres de archivo.
  - Excepción explícita: `__init__.py`.
- **Clases**: `PascalCase`.

## 3) Prefijos/sufijos recomendados por rol
Usar estos sufijos para facilitar lectura arquitectónica:
- `*_use_case`
- `*_puerto`
- `*_repositorio`
- `*_controlador`
- `*_vista`

> Nota: Son recomendaciones fuertes para nuevas piezas. No fuerzan migración inmediata del histórico.

## 4) Scripts canónicos
En la raíz del repo, los nombres canónicos esperados son:
- `lanzar_app.bat`
- `ejecutar_tests.bat`
- `update.bat` **(si existe en el proyecto)**

Se permite mantener scripts legacy por compatibilidad, pero para nueva documentación y automatizaciones se deben priorizar los canónicos.

## 5) Guardarraíl automático (solo nuevas incorporaciones)
Existe un test de `pytest` que valida naming de archivos `.py` dentro de `app/`:
- Si un archivo ya está en baseline (`configuracion/baseline_naming.json`), se permite temporalmente.
- Si es nuevo y no está en baseline, debe cumplir convención.

## 6) Cómo actualizar baseline (solo cuando sea estrictamente necesario)
1. Justificar por qué el archivo no puede cumplir convención ahora.
2. Añadir la ruta relativa a `archivos_existentes_permitidos` en `configuracion/baseline_naming.json`.
3. Mantener la lista mínima; no agregar rutas innecesarias.

Comando útil para inspección local:

```bash
python - <<'PY'
from pathlib import Path
import re
for p in sorted(Path('app').rglob('*.py')):
    n = p.name
    if n != '__init__.py' and not re.fullmatch(r'[a-z0-9_]+\\.py', n):
        print(p.as_posix())
PY
```
