"""Admin Django : comptes de l'équipe et rôle animateur."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


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
