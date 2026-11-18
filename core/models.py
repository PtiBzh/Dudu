"""Modèles de Dudu.

M0 : comptes identifiés + rôle animateur.
M1 : postes de travail, cotation santé/sécurité, traçabilité des éditions.

Règles de gestion (Spec Dudu.md) :
1. Rien ne disparaît : un poste n'est jamais supprimé, au mieux archivé.
3. Le statut de satisfaction n'est modifié qu'en revue collégiale.
4. Création libre ; édition par l'animateur tracée « modifiée par X le Y ».
"""
from django.conf import settings
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


class Lieu(models.Model):
    """Lieu du club (Hangar, Parc, Accueil…) — liste modifiable dans
    l'admin, sert de filtre rapide des postes."""

    nom = models.CharField("nom", max_length=100, unique=True)
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta:
        verbose_name = "lieu"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class ValeurCotation(models.Model):
    """Socle commun des listes de valeurs (libellé + ordre)."""

    libelle = models.CharField("libellé", max_length=50)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        abstract = True
        ordering = ["ordre", "libelle"]

    def __str__(self):
        return self.libelle


class ValeurSatisfaction(ValeurCotation):
    """Valeur de satisfaction d'un poste (défaut : Satisfaisant /
    À améliorer / Critique). Assignée uniquement en revue (règle 3),
    donc absente du formulaire de création."""

    couleur = models.CharField(
        "couleur",
        max_length=20,
        default="#6b7684",
        help_text="Code hexadécimal du marqueur carte, ex. #0d6b7c",
    )

    class Meta(ValeurCotation.Meta):
        verbose_name = "valeur de satisfaction"
        verbose_name_plural = "valeurs de satisfaction"


class ValeurGravite(ValeurCotation):
    """Gravité potentielle — bloc santé/sécurité du poste."""

    class Meta(ValeurCotation.Meta):
        verbose_name = "valeur de gravité"
        verbose_name_plural = "valeurs de gravité"


class ValeurFrequence(ValeurCotation):
    """Fréquence d'exposition — bloc santé/sécurité du poste."""

    class Meta(ValeurCotation.Meta):
        verbose_name = "valeur de fréquence"
        verbose_name_plural = "valeurs de fréquence"


class Poste(models.Model):
    """Un aspect récurrent du travail au club.
    Exemples : Manutention remorque planches, Accueil des gens, Vestiaire mono.
    """

    class Origine(models.TextChoices):
        """Origine du signalement (bloc santé/sécurité)."""
        CONSTAT = "constat", "Constat"
        PRESQU_ACCIDENT = "presqu_accident", "Presqu'accident"
        ACCIDENT = "accident", "Accident"

    nom = models.CharField("nom", max_length=150)
    description = models.TextField("description", blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.PROTECT,
        related_name="postes_crees",
    )
    lieu = models.ForeignKey(
        Lieu,
        verbose_name="lieu",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="postes",
    )
    date_creation = models.DateTimeField("créé le", auto_now_add=True)

    # Position sur la carte — obligatoire à partir de M3 (clic carte) ;
    # optionnelle en M1/M2 (noyau utilisable sans carte).
    latitude = models.FloatField("latitude", null=True, blank=True)
    longitude = models.FloatField("longitude", null=True, blank=True)

    # Bloc santé/sécurité : modifiable à tout moment (état constaté).
    gravite = models.ForeignKey(
        ValeurGravite,
        verbose_name="gravité potentielle",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="postes",
    )
    frequence = models.ForeignKey(
        ValeurFrequence,
        verbose_name="fréquence d'exposition",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="postes",
    )
    origine = models.CharField(
        "origine du signalement",
        max_length=20,
        choices=Origine.choices,
        default=Origine.CONSTAT,
    )

    # Statut de satisfaction : uniquement via les revues (M4).
    satisfaction = models.ForeignKey(
        ValeurSatisfaction,
        verbose_name="statut de satisfaction",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="postes",
    )

    archive = models.BooleanField("archivé", default=False)

    class Meta:
        verbose_name = "poste"
        ordering = ["lieu__ordre", "lieu__nom", "nom"]

    def __str__(self):
        return self.nom

    def peut_etre_modifie_par(self, utilisateur):
        """L'auteur peut retoucher sa saisie ; l'animateur peut trier
        (fusion des doublons, mise en forme). Personne d'autre."""
        return utilisateur.is_animateur or utilisateur.pk == self.auteur_id

    def delete(self, *args, **kwargs):
        """Règle 1 : rien ne disparaît. Un poste s'archive, jamais ne
        se supprime. Les vues n'exposent pas la suppression, l'admin
        l'interdit, et le modèle lui-même refuse."""
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(
            "Un poste ne se supprime pas : il s'archive (règle 1)."
        )


class EditionPoste(models.Model):
    """Trace « modifiée par X le Y » (règle 4) : chaque édition
    enregistrée via l'app journalise qui et quand."""

    poste = models.ForeignKey(
        Poste,
        verbose_name="poste",
        on_delete=models.CASCADE,
        related_name="editions",
    )
    qui = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="modifié par",
        on_delete=models.PROTECT,
        related_name="editions_poste",
    )
    quand = models.DateTimeField("le", auto_now_add=True)

    class Meta:
        verbose_name = "édition de poste"
        verbose_name_plural = "éditions de poste"
        ordering = ["-quand"]

    def __str__(self):
        return f"{self.poste} modifié par {self.qui}"
