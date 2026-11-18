"""Routage de l'application core (postes, actions)."""
from django.urls import path

from . import views

urlpatterns = [
    path("postes/", views.postes, name="postes"),
    path("postes/nouveau/", views.poste_creer, name="poste_creer"),
    path("postes/<int:pk>/", views.poste_detail, name="poste_detail"),
    path("postes/<int:pk>/modifier/", views.poste_modifier, name="poste_modifier"),
    path("postes/<int:pk>/archiver/", views.poste_archiver, name="poste_archiver"),
    path("actions/", views.actions, name="actions"),
    path(
        "postes/<int:poste_pk>/actions/nouveau/",
        views.action_creer,
        name="action_creer",
    ),
    path("actions/<int:pk>/", views.action_detail, name="action_detail"),
    path("actions/<int:pk>/modifier/", views.action_modifier, name="action_modifier"),
]
