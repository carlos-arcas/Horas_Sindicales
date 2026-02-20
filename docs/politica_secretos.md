# Política mínima anti-secretos

## Qué no se sube nunca al repositorio
No se deben versionar, ni siquiera temporalmente:
- Credenciales o tokens (`credentials*.json`, `token*.json`, `client_secret*.json`).
- Variables de entorno y ficheros `.env`.
- Bases de datos locales (`*.db`, `*.sqlite`, `*.sqlite3`, `*.db-journal`).
- Exportaciones con datos potencialmente sensibles (`*.csv`, `*.pdf`) y logs (`*.log`).

## Dónde guardar credenciales
- Guardar secretos fuera del árbol del proyecto.
- En Windows, usar una ruta de usuario como `%AppData%` o `%LocalAppData%` con permisos restringidos.
- En Linux/macOS, usar directorios de usuario con permisos mínimos (por ejemplo `~/.config/<app>`).

## Respuesta ante una filtración
1. **Revocar/rotar** inmediatamente la credencial comprometida.
2. **Eliminar exposición futura**: mover el secreto fuera del repo y reforzar `.gitignore`.
3. **Limpiar historial** si procede (reescritura de historial y coordinación del equipo).
4. **Notificar** al equipo y registrar incidente, alcance y acciones correctivas.

## Verificación continua
Este repositorio incluye tests automáticos para:
- Comprobar patrones críticos en `.gitignore`.
- Detectar ficheros prohibidos presentes en el árbol de trabajo.
