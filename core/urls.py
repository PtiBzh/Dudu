"""Routage de l'application core (postes)."""
from django.urls import path

from . import views

urlpatterns = [
    path("postes/", views.postes, name="postes"),
    path("postes/nouveau/", views.poste_creer, name="poste_creer"),
    path("postes/<int:pk>/", views.poste_detail, name="poste_detail"),
    path("postes/<int:pk>/modifier/", views.poste_modifier, name="poste_modifier"),
    path("postes/<int:pk>/archiver/", views.poste_archiver, name="poste_archiver"),
]
