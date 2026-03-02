# Migración i18n: aliases legacy sin línea

## Problema del baseline `ruta:línea:texto`
El baseline actual identifica hardcodeos con `ruta:línea:texto`. Ese enfoque es frágil porque al mover código (refactor, imports, helpers) cambia la línea y la referencia deja de coincidir aunque el texto siga siendo el mismo.

## Solución: alias por `ruta+texto` (sin línea)
Se añadió `.config/ui_strings_aliases.json` con un índice `alias_legacy_sin_linea`.

- Cada alias se calcula con `build_legacy_alias(path, text)`.
- El alias usa un hash corto determinista de `path + text`.
- `GestorI18N.t(...)` resuelve en este orden:
  1. key semántica en catálogo.
  2. `fallback=` si la key no existe (con warning `i18n_missing_key`).
  3. key legacy `ruta:línea:texto` convertida a alias `ruta+texto` (ignorando línea).
  4. marcador seguro `[i18n:{key}]` + error estructurado.

## Workflow recomendado (incremental por archivo)
1. Elegir un archivo UI.
2. Reemplazar literales por `i18n.t("clave.semantica", fallback="Texto original")`.
3. Añadir las claves semánticas al catálogo (`catalogo_es.json` y placeholders en otros idiomas).
4. Registrar en `.config/ui_strings_aliases.json` cada `path+text -> key_semantica` del archivo migrado.
5. Añadir tests de resolución semántica, fallback, alias y marcador final.
