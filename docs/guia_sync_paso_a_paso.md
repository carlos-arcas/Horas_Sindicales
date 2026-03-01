# Guía Sync paso a paso (para delegadas)

## ¿Qué es el Sync y por qué lo necesitamos?

El **Sync** (sincronización) es el mecanismo que permite que varias delegadas trabajen con la misma información, sin perder cambios y manteniendo los datos alineados en todo el grupo.

En la práctica, sirve para:

- Compartir altas y cambios de solicitudes entre delegadas.
- Evitar que cada equipo tenga "su versión" aislada de los datos.
- Mantener un historial común para seguimiento y control.

Si hay un grupo de delegadas trabajando sobre el mismo colectivo, el Sync es la forma de mantener todo coordinado.

## ¿Qué son las credenciales y quién debe tenerlas?

Las **credenciales** son los datos de acceso que autorizan a la aplicación a conectarse al archivo compartido del grupo.

Puntos clave:

- El grupo necesita una configuración de credenciales válida para poder sincronizar.
- No hace falta que todas las personas creen credenciales nuevas: normalmente las prepara una persona responsable técnica/organizativa y las comparte de forma segura con el resto del grupo.
- Todas las delegadas que vayan a usar Sync deben tener acceso al mismo recurso compartido configurado por el grupo.

## Cómo obtener las credenciales (paso a paso)

1. Definir quién será la persona responsable de preparar el acceso del grupo.
2. Crear (o identificar) el archivo compartido que se usará para sincronizar.
3. Generar las credenciales de acceso para la aplicación.
4. Verificar que esas credenciales tienen permisos sobre el archivo compartido.
5. Compartir las credenciales **solo** con las delegadas autorizadas del grupo.
6. Configurar la aplicación con esas credenciales en cada equipo.
7. Hacer una primera sincronización de prueba para confirmar que funciona.

> Recomendación: dejar por escrito dentro del grupo quién custodiará las credenciales y cómo se hará la actualización cuando cambien.

## Problemas típicos y soluciones rápidas

### 1) "No conecta" o "No sincroniza"

Posibles causas:

- Credenciales mal copiadas o incompletas.
- Archivo compartido incorrecto.
- Falta de permisos.

Qué hacer:

- Revisar que la credencial cargada es la vigente.
- Confirmar que el grupo está apuntando al archivo correcto.
- Verificar permisos del recurso compartido.

### 2) "A mí me funciona y a otra delegada no"

Posibles causas:

- Configuraciones diferentes entre equipos.
- Una persona tiene una versión antigua de credenciales.

Qué hacer:

- Unificar la configuración del grupo.
- Reenviar la versión actual de credenciales por el canal acordado.

### 3) Cambios que "desaparecen" o no se ven enseguida

Posibles causas:

- Sincronización no ejecutada después de cargar cambios.
- Conflictos por ediciones simultáneas.

Qué hacer:

- Ejecutar Sync al terminar una tanda de cambios.
- Repetir Sync y comprobar el estado.
- Si persiste, coordinar quién edita cada bloque para evitar solapamientos.

## Seguridad básica (imprescindible)

- **No publicar** credenciales en chats abiertos, capturas, correos masivos o documentos públicos.
- Compartirlas solo con personas autorizadas del grupo.
- Guardarlas en ubicaciones seguras y controladas.
- Si se sospecha filtración o acceso indebido, **revocar y rotar** credenciales cuanto antes.
- Tras rotar, avisar al grupo y actualizar la configuración en todos los equipos.

La seguridad de las credenciales protege tanto el trabajo del grupo como la integridad de los datos sincronizados.
