"""Routage de l'application core (postes, actions, carte, revues,
photos)."""
from django.urls import path

from . import views

urlpatterns = [
    path("carte/", views.carte, name="carte"),
    path("revues/", views.revues, name="revues"),
    path("revues/nouvelle/", views.revue_creer, name="revue_creer"),
    path("revues/<int:pk>/", views.revue_detail, name="revue_detail"),
    path("revues/<int:pk>/modifier/", views.revue_modifier, name="revue_modifier"),
    path("revues/<int:pk>/postes/", views.revue_poste_ajouter, name="revue_poste_ajouter"),
    path(
        "revues/<int:pk>/postes/<int:poste_pk>/retirer/",
        views.revue_poste_retirer,
        name="revue_poste_retirer",
    ),
    path(
        "revues/<int:pk>/postes/<int:poste_pk>/satisfaction/",
        views.revue_satisfaction,
        name="revue_satisfaction",
    ),
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
    path(
        "postes/<int:poste_pk>/photos/",
        views.poste_photo_ajouter,
        name="poste_photo_ajouter",
    ),
    path(
        "actions/<int:pk>/photos/",
        views.action_photo_ajouter,
        name="action_photo_ajouter",
    ),
]
