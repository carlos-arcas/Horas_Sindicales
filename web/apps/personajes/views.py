from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from web.apps.personajes.models import PersonajeModel


def personajes_lista_crear(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        PersonajeModel.objects.create(
            proyecto_id=request.POST.get("proyecto_id"),
            nombre=request.POST.get("nombre", ""),
            descripcion=request.POST.get("descripcion", ""),
        )
        return redirect("personajes_lista")
    return render(request, "personajes/lista.html", {"personajes": PersonajeModel.objects.all()})


def personaje_editar(request: HttpRequest, personaje_id: str) -> HttpResponse:
    personaje = PersonajeModel.objects.get(id=personaje_id)
    if request.method == "POST":
        personaje.nombre = request.POST.get("nombre", personaje.nombre)
        personaje.descripcion = request.POST.get("descripcion", personaje.descripcion)
        personaje.save(update_fields=["nombre", "descripcion", "updated_at"])
        return redirect("personajes_lista")
    return render(request, "personajes/editar.html", {"personaje": personaje})


def personaje_eliminar(request: HttpRequest, personaje_id: str) -> HttpResponse:
    personaje = PersonajeModel.objects.get(id=personaje_id)
    if request.method == "POST":
        personaje.delete()
        return redirect("personajes_lista")
    return render(request, "personajes/eliminar.html", {"personaje": personaje})
