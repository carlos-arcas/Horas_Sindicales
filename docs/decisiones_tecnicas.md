# Decisiones técnicas de dependencias

## Por qué pinneamos dependencias

Para asegurar builds reproducibles en local, CI y Windows (`.bat` canónicos), las instalaciones se realizan desde archivos pinneados con versión exacta (`==`). Esto evita variaciones por resolución de dependencias cuando se usan rangos (`>=`, `<`).

## Fuente humana vs. lock reproducible

- `requirements.in`: fuente humana de dependencias runtime (con intención/rango).
- `requirements-dev.in`: fuente humana de dependencias de desarrollo y testing.
- `requirements.txt`: salida pinneada para instalación runtime.
- `requirements-dev.txt`: salida pinneada para desarrollo/testing.

En este repositorio usamos **pip-tools** como herramienta estándar de compilación.

## Cómo actualizar dependencias

1. Editar únicamente `requirements.in` y/o `requirements-dev.in`.
2. Regenerar lockfiles con:

```bash
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

3. Ejecutar tests:

```bash
pytest -q
```

4. Commit de los cuatro archivos de dependencias (`.in` y `.txt`).

## Nota de plataforma

No se ha separado por plataforma porque las dependencias actuales son compatibles con el flujo objetivo. Si en el futuro aparece una dependencia específica de SO, se deberá declarar con markers de entorno (`; sys_platform == ...`) y documentar el motivo.
