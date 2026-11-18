"""Admin Django : équipes, rôles, postes et listes de valeurs.

L'admin sert aussi de « rattrapage » (corrections de saisie) ; en
revanche, la suppression de postes y est désactivée (règle 1 : rien
ne disparaît).
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Action,
    EditionPoste,
    Lieu,
    Poste,
    Utilisateur,
    ValeurFrequence,
    ValeurGravite,
    ValeurSatisfaction,
)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "is_animateur",
        "is_active",
    )
    list_filter = UserAdmin.list_filter + ("is_animateur",)
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle Dudu", {"fields": ("is_animateur",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle Dudu", {"fields": ("is_animateur",)}),
    )


@admin.register(Lieu)
class LieuAdmin(admin.ModelAdmin):
    list_display = ("nom", "ordre")


@admin.register(ValeurSatisfaction)
class ValeurSatisfactionAdmin(admin.ModelAdmin):
    list_display = ("libelle", "ordre", "couleur")


@admin.register(ValeurGravite)
class ValeurGraviteAdmin(admin.ModelAdmin):
    list_display = ("libelle", "ordre")


@admin.register(ValeurFrequence)
class ValeurFrequenceAdmin(admin.ModelAdmin):
    list_display = ("libelle", "ordre")


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    """Consultation et rattrapage ; suppression interdite."""

    list_display = (
        "nom",
        "lieu",
        "auteur",
        "origine",
        "gravite",
        "frequence",
        "satisfaction",
        "archive",
    )
    list_filter = ("lieu", "origine", "archive", "satisfaction")
    search_fields = ("nom", "description")

    def has_delete_permission(self, request, obj=None):
        return False  # règle 1 : rien ne disparaît


@admin.register(EditionPoste)
class EditionPosteAdmin(admin.ModelAdmin):
    list_display = ("poste", "qui", "quand")
    search_fields = ("poste__nom", "qui__username")

    def has_delete_permission(self, request, obj=None):
        return False  # la trace est la trace


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """Consultation et rattrapage ; suppression interdite (règle 1)."""

    list_display = ("intitule", "poste", "responsable", "echeance", "statut")
    list_filter = ("statut", "responsable")
    search_fields = ("intitule", "description", "poste__nom")
    date_hierarchy = "echeance"

    def has_delete_permission(self, request, obj=None):
        return False  # règle 1 : rien ne disparaît
