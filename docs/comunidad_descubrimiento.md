# Descubrimiento de comunidad (demo)

## Cargar contenido demo

```bash
python -m scripts.cargar_comunidad_demo
```

Resultado esperado en logs:
- carga de perfiles demo;
- carga de publicaciones demo;
- operación idempotente (si se ejecuta dos veces no duplica registros).

## Probar rápidamente

1. Ejecutar el comando de carga demo.
2. Consultar desde código el caso de uso `DescubrirComunidadCasoUso` con filtros `recientes` y `populares`.
3. Verificar que la pestaña `siguiendo` queda deshabilitada (`pestaña_siguiendo_habilitada=False`) hasta contar con relación real de seguimiento.

## Diseño

- No se agregan dependencias externas.
- Se reutiliza SQLite + migraciones existentes.
- El feed soporta ordenación por recientes/populares, filtro por disciplina y búsqueda textual simple en título/resumen.
