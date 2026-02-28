# Tutorial rápido (sin tecnicismos)

## 1) Cómo usar la pantalla de **Solicitudes**

1. **Elige la delegada**.
2. Selecciona la **fecha**.
3. Completa el tramo **Desde / Hasta** (o marca **Completo**).
4. (Opcional) añade **Notas**.
5. Pulsa **Añadir pendiente**.

### Qué verás ahora
- **Ayudas cortas** en cada campo crítico (delegada, fecha, tramo, minutos, notas).
- Un resumen claro de errores arriba cuando falta algo.
- Si hay error, el foco va al **primer campo a corregir**.
- Un panel de estado siempre visible:
  - **Listo**: puedes seguir trabajando.
  - **Guardado**: se guardó correctamente.
  - **Pendiente de sync**: hay cambios locales aún no enviados a Google Sheets.
  - **Error**: revisa campos marcados o vuelve a intentar.

### Tips útiles
- **Tip:** pulsa Enter para guardar más rápido.
- **Tip:** 90 minutos = 1h 30min.
- **Tip:** marca “Completo” cuando sea una jornada completa.

### Mostrar/Ocultar ayuda
- Usa el switch **“Mostrar ayuda”** para ver u ocultar tooltips ampliados.
- La preferencia queda guardada para próximas aperturas.

---

## 2) Configurar Sync como asistente (Google Sheets)

Abre **Configuración > Conexión Google Sheets** y sigue estos pasos:

### Paso 1 · Qué necesitas
- URL o ID de la hoja.
- Archivo JSON de credenciales (cuenta de servicio).

### Paso 2 · Cargar credenciales
- Pega la URL/ID.
- Pulsa **Seleccionar credenciales JSON…**.

### Paso 3 · Probar conexión
- Pulsa **Probar conexión**.
- Verás mensajes claros si algo falla (sin detalles técnicos confusos).

### Paso 4 · Guardar y finalizar
- Pulsa **Guardar**.
- Si todo está bien, ya puedes sincronizar.

---

## 3) Si aparece un error de Sync, qué hacer

La app ya te indica la acción recomendada para casos comunes:
- Archivo no encontrado.
- Permiso denegado.
- Credenciales inválidas.
- Sin acceso a la hoja.
- Límite temporal de Google.

En todos los casos: corrige lo indicado y vuelve a usar **Probar conexión**.
