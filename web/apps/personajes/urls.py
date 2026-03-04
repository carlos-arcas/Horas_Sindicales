from __future__ import annotations

from django.urls import path

from web.apps.personajes import views

urlpatterns = [
    path("", views.personajes_lista_crear, name="personajes_lista"),
    path("<uuid:personaje_id>/editar/", views.personaje_editar, name="personajes_editar"),
    path("<uuid:personaje_id>/eliminar/", views.personaje_eliminar, name="personajes_eliminar"),
]
