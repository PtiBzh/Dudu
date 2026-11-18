"""Modèles de Dudu — M0 : utilisateurs et rôles.

Les postes, actions, revues, photos et plans de bâtiments arrivent
aux jalons M1 et suivants.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Membre de l'équipe du centre nautique.

    Sur Dudu, tout est identifié : pas d'anonymat (spec fonctionnelle).
    Le rôle d'animateur de l'app est un simple drapeau assignable :
    un rôle de secrétariat, pas un décisionnaire.
    """

    is_animateur = models.BooleanField(
        "animateur de l'app",
        default=False,
        help_text="Peut trier les postes et créer une action urgente hors revue.",
    )

    class Meta:
        verbose_name = "utilisateur"
        ordering = ["last_name", "first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username
