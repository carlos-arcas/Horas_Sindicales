# Seguridad SQL

## Reglas obligatorias

- Toda consulta SQL debe usar parámetros (`?`) para **datos variables**.
- `executescript` está **prohibido en runtime** y solo se permite en migraciones.
- Los tests de seguridad deben validar que no hay interpolación SQL y que payloads maliciosos no rompen tablas.

## Ejemplos

### ✅ Bien

```python
cursor.execute("SELECT * FROM personas WHERE nombre = ?", (nombre,))
```

### ❌ Mal

```python
cursor.execute(f"SELECT * FROM personas WHERE nombre = '{nombre}'")
cursor.executescript(user_sql)
```
