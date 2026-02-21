# Ubicación de la base de datos SQLite en runtime

La aplicación crea la base de datos local en:

- Windows: `%LOCALAPPDATA%\\HorasSindicales\\data\\horas_sindicales.db`
- Linux/macOS: `~/.local/share/HorasSindicales/data/horas_sindicales.db`

También se puede sobrescribir con la variable de entorno `HORAS_DB_PATH`.

Este archivo (`horas_sindicales.db`) y cualquier `*.db` están ignorados por Git para evitar que datos locales o sensibles entren en el repositorio.

Si en algún momento `horas_sindicales.db` quedó trackeado por error, desasócialo sin borrar tu copia local con:

```bash
git rm --cached horas_sindicales.db
```
