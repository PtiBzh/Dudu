"""Routage de l'application core (postes, actions, carte, revues,
photos, plans)."""
from django.urls import path

from . import views

urlpatterns = [
    path("carte/", views.carte, name="carte"),
    path(
        "medias/<path:chemin>",
        views.medias,
        name="medias",
    ),
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
    # M9 — passage guidé : sélection en bloc puis examen un par un.
    path(
        "revues/<int:pk>/selection/",
        views.revue_selection,
        name="revue_selection",
    ),
    path(
        "revues/<int:pk>/passage/",
        views.revue_passage_debut,
        name="revue_passage_debut",
    ),
    path(
        "revues/<int:pk>/passage/<int:poste_pk>/",
        views.revue_passage,
        name="revue_passage",
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
        "actions/<int:pk>/statut/<str:statut>/",
        views.action_statut,
        name="action_statut",
    ),
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
    path("plans/", views.plans, name="plans"),
    path("plans/nouveau/", views.plan_nouveau, name="plan_nouveau"),
    path(
        "plans/<int:pk>/modifier/",
        views.plan_modifier,
        name="plan_modifier",
    ),
    path("plans/<int:pk>/dessin/", views.plan_dessin, name="plan_dessin"),
    path("plans/<int:pk>/calage/", views.plan_calage, name="plan_calage"),
    path(
        "plans/<int:pk>/supprimer/",
        views.plan_supprimer,
        name="plan_supprimer",
    ),
    path("equipe/", views.equipe, name="equipe"),
    path("equipe/nouveau/", views.equipe_creer, name="equipe_creer"),
    path(
        "equipe/<int:pk>/modifier/",
        views.equipe_modifier,
        name="equipe_modifier",
    ),
    path("parametres/", views.parametres, name="parametres"),
    path("parametres/carte/", views.parametres_carte, name="parametres_carte"),
    path(
        "parametres/<slug:liste>/ajouter/",
        views.parametres_valeur_ajouter,
        name="parametres_valeur_ajouter",
    ),
    path(
        "parametres/<slug:liste>/<int:pk>/modifier/",
        views.parametres_valeur_modifier,
        name="parametres_valeur_modifier",
    ),
    path(
        "parametres/<slug:liste>/<int:pk>/supprimer/",
        views.parametres_valeur_supprimer,
        name="parametres_valeur_supprimer",
    ),
]
