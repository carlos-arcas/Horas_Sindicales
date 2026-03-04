from __future__ import annotations

import uuid

from django.db import models


class PersonajeModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto_id = models.UUIDField(db_index=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personajes"
