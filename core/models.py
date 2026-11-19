"""Modèles de Dudu.

M0 : comptes identifiés + rôle animateur.
M1 : postes de travail, cotation santé/sécurité, traçabilité des éditions.
M2 : actions d'amélioration (responsable et échéance obligatoires).
M3 : couleurs des valeurs de cotation pour les marqueurs carte.
M4 : revues collégiales — journal historique des décisions.
M5 : photos avant/après, compressées à l'upload, datant la clôture.
M6 : plans de bâtiments — formes dessinées (Terra Draw) ou images
calées (4 coins WGS84), affichés sous les marqueurs.

Règles de gestion (Spec Dudu.md) :
1. Rien ne disparaît : un poste n'est jamais supprimé, au mieux archivé ;
   une action abandonnée reste visible avec son motif.
2. Une action sans responsable ni échéance ne peut pas être créée.
3. Le statut de satisfaction n'est modifié qu'en revue collégiale.
4. Création libre ; édition par l'animateur tracée « modifiée par X le Y ».
5. Un risque grave ne patiente pas : action urgente hors revue, par
   l'animateur.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
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
    """Socle commun des listes de valeurs : libellé, ordre et couleur
    du marqueur carte (remplissage = santé/sécurité, halo =
    satisfaction, teintes des états d'action)."""

    libelle = models.CharField("libellé", max_length=50)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)
    couleur = models.CharField(
        "couleur",
        max_length=20,
        default="#6b7684",
        help_text="Code hexadécimal du marqueur carte, ex. #0d6b7c",
    )

    class Meta:
        abstract = True
        ordering = ["ordre", "libelle"]

    def __str__(self):
        return self.libelle


class ValeurSatisfaction(ValeurCotation):
    """Valeur de satisfaction d'un poste (défaut : Satisfaisant /
    À améliorer / Critique). Assignée uniquement en revue (règle 3),
    donc absente du formulaire de création. Sa couleur dessine le halo
    du marqueur carte du poste."""

    class Meta(ValeurCotation.Meta):
        verbose_name = "valeur de satisfaction"
        verbose_name_plural = "valeurs de satisfaction"


class ValeurGravite(ValeurCotation):
    """Gravité potentielle — bloc santé/sécurité du poste. Sa couleur
    remplit le marqueur carte (M3)."""

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

    # Position sur la carte (WGS84) — obligatoire depuis M3 : le
    # formulaire place le poste d'un clic sur la mini-carte. Le champ
    # reste nullable en base pour ne pas casser les données saisies
    # avant la carte.
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


class Action(models.Model):
    """Action d'amélioration décidée pour un poste.

    Créée en revue collégiale (M4) ou en urgence hors revue par
    l'animateur si le risque est grave (règle 5) : elle est alors inscrite
    d'office à la prochaine revue. Un poste peut porter plusieurs actions
    suivies en parallèle.
    """

    class Statut(models.TextChoices):
        """Statut de réalisation."""
        A_FAIRE = "a_faire", "À faire"
        EN_COURS = "en_cours", "En cours"
        FAITE = "faite", "Faite"
        ABANDONNEE = "abandonnee", "Abandonnée"

    poste = models.ForeignKey(
        Poste,
        verbose_name="poste",
        on_delete=models.PROTECT,
        related_name="actions",
    )
    intitule = models.CharField("intitulé", max_length=150)
    description = models.TextField("description de travail", blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable",
        on_delete=models.PROTECT,
        related_name="actions_portees",
    )
    echeance = models.DateField("échéance")
    statut = models.CharField(
        "statut de réalisation",
        max_length=20,
        choices=Statut.choices,
        default=Statut.A_FAIRE,
    )
    motif_abandon = models.TextField("motif d'abandon", blank=True)
    date_creation = models.DateTimeField("créée le", auto_now_add=True)
    date_cloture = models.DateTimeField(
        "clôturée le",
        null=True,
        blank=True,
        help_text="Automatique au passage en « faite » ; effacée si "
        "l'action se rouvre. Sert aux revues : actions clôturées "
        "depuis la revue précédente.",
    )

    # Position héritée du poste à la création, modifiable ensuite.
    latitude = models.FloatField("latitude", null=True, blank=True)
    longitude = models.FloatField("longitude", null=True, blank=True)

    # Revue de création : preuve de la décision collégiale (M4). Vide
    # pour une action urgente créée hors revue (règle 5), inscrite
    # d'office à la prochaine revue.
    revue = models.ForeignKey(
        "Revue",
        verbose_name="revue de création",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="actions",
    )

    class Meta:
        verbose_name = "action"
        ordering = ["echeance", "date_creation"]

    def __str__(self):
        return self.intitule

    @property
    def est_ouverte(self):
        return self.statut in (self.Statut.A_FAIRE, self.Statut.EN_COURS)

    def save(self, *args, **kwargs):
        """La clôture se date, la réouverture l'efface : les revues
        affichent les actions accomplies depuis la précédente. La
        photo « après » reste demandée (avertissement), jamais
        exigée (spec : non bloquant)."""
        from django.utils import timezone

        if self.statut == self.Statut.FAITE:
            if self.date_cloture is None:
                self.date_cloture = timezone.now()
        else:
            self.date_cloture = None
        super().save(*args, **kwargs)

    @property
    def en_retard(self):
        """Ouverte (à faire ou en cours) dont l'échéance est passée.
        Une action faite ou abandonnée n'est jamais « en retard »."""
        from django.utils import timezone

        return self.est_ouverte and self.echeance < timezone.localdate()

    def peut_etre_modifiee_par(self, utilisateur):
        """Le responsable de l'action ou l'animateur."""
        return utilisateur.is_animateur or utilisateur.pk == self.responsable_id

    def delete(self, *args, **kwargs):
        """Règle 1 : une action ne se supprime pas. Abandonnée, elle
        reste visible avec son motif ; faite, elle témoigne du chemin
        parcouru."""
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(
            "Une action ne se supprime pas : abandonnée, elle reste "
            "visible avec son motif (règle 1)."
        )


class Revue(models.Model):
    """Revue de réunion — journal historique des choix de l'équipe
    (M4). La satisfaction d'un poste ne se décide qu'ici (règle 3) ;
    chaque changement est consigné via ChangementSatisfaction. Les
    actions décidées collégialement y sont rattachées ; les urgentes
    créées hors revue par l'animateur restent visibles à part.
    """

    date = models.DateField("date de la revue")
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="participants",
        blank=True,
        related_name="revues_participees",
    )
    postes = models.ManyToManyField(
        Poste,
        verbose_name="postes examinés",
        blank=True,
        related_name="revues",
    )
    compte_rendu = models.TextField("compte rendu", blank=True)
    date_creation = models.DateTimeField("enregistrée le", auto_now_add=True)

    class Meta:
        verbose_name = "revue"
        ordering = ["-date", "-date_creation"]

    def __str__(self):
        return f"Revue du {self.date:%d/%m/%Y}"

    def delete(self, *args, **kwargs):
        """Règle 1 : une revue est un journal historique, elle ne
        disparaît jamais."""
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(
            "Une revue ne se supprime pas : c'est le journal "
            "historique de l'équipe (règle 1)."
        )


class ChangementSatisfaction(models.Model):
    """Une décision de satisfaction prise en revue (règle 3) :
    ancienne valeur, nouvelle valeur — le journal historique du poste.
    Ancienne vide = première décision du poste."""

    revue = models.ForeignKey(
        Revue,
        verbose_name="revue",
        on_delete=models.PROTECT,
        related_name="changements",
    )
    poste = models.ForeignKey(
        Poste,
        verbose_name="poste",
        on_delete=models.PROTECT,
        related_name="changements_satisfaction",
    )
    ancienne = models.ForeignKey(
        ValeurSatisfaction,
        verbose_name="ancienne valeur",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="changements_depuis",
    )
    nouvelle = models.ForeignKey(
        ValeurSatisfaction,
        verbose_name="nouvelle valeur",
        on_delete=models.PROTECT,
        related_name="changements_vers",
    )
    quand = models.DateTimeField("le", auto_now_add=True)

    class Meta:
        verbose_name = "changement de satisfaction"
        verbose_name_plural = "changements de satisfaction"
        ordering = ["-quand"]

    def __str__(self):
        ancienne = str(self.ancienne) if self.ancienne else "à décider"
        return f"{self.poste} : {ancienne} → {self.nouvelle} ({self.revue})"

    def delete(self, *args, **kwargs):
        """Le journal est le journal : une décision consignée ne
        s'efface pas."""
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(
            "Un changement de satisfaction ne se supprime pas : le "
            "journal historique est immuable."
        )


def dossier_photos(instance, filename):
    """Spec technique : les photos vivent sous /data/photos/AAAA/
    (MEDIA_ROOT se règle par DUDU_DATA en production)."""
    from django.utils import timezone

    return f"photos/{timezone.localdate().year}/{filename}"


class Photo(models.Model):
    """Photo avant (situation constatée, rattachée au poste) ou
    après (travail accompli, rattachée à l'action). Redimensionnée
    et recompressée à l'upload (~1600 px JPEG, spec technique) :
    le volume /data reste léger, l'original n'est pas conservé.
    """

    class Type(models.TextChoices):
        AVANT = "avant", "Avant"
        APRES = "apres", "Après"

    type = models.CharField("type", max_length=10, choices=Type.choices)
    fichier = models.ImageField("fichier", upload_to=dossier_photos)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.PROTECT,
        related_name="photos_ajoutees",
    )
    poste = models.ForeignKey(
        Poste,
        verbose_name="poste",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="photos_avant",
    )
    action = models.ForeignKey(
        Action,
        verbose_name="action",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="photos_apres",
    )
    date = models.DateTimeField("ajoutée le", auto_now_add=True)

    class Meta:
        verbose_name = "photo"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.poste or self.action}"

    def clean(self):
        """« Avant » documente un poste, « après » une action : pas de
        photo flottante, pas de rattachement croisé. Les vues créent
        déjà les photos bien rattachées ; ce garde-fou couvre l'admin."""
        from django.core.exceptions import ValidationError

        if self.type == self.Type.AVANT:
            if self.poste is None:
                raise ValidationError(
                    "Une photo « avant » se rattache à un poste."
                )
            if self.action is not None:
                raise ValidationError(
                    "Une photo « avant » documente un poste, pas une action."
                )
        elif self.type == self.Type.APRES:
            if self.action is None:
                raise ValidationError(
                    "Une photo « après » se rattache à une action."
                )
            if self.poste is not None:
                raise ValidationError(
                    "Une photo « après » documente une action, pas un poste."
                )

    def delete(self, *args, **kwargs):
        """Règle 1 : une photo témoigne, elle ne disparaît pas."""
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(
            "Une photo ne se supprime pas : elle témoigne du chemin "
            "parcouru (règle 1)."
        )


def dossier_plans(instance, filename):
    """Spec technique : les plans calés vivent dans /data/plans/
    (MEDIA_ROOT se règle par DUDU_DATA en production)."""
    return f"plans/{filename}"


class PlanBatiment(models.Model):
    """Plan d'un bâtiment (M6), affiché sous les marqueurs de la carte.

    Deux natures, au choix (spec technique) : une forme polygone
    dessinée à la souris (Terra Draw, page de dessin), ou une image
    importée (PNG/JPG) calée par ses 4 coins en WGS84, déplacée à la
    souris par poignées de coin. Les étages se dessinent côte à côte
    (« chez le voisin »), jamais empilés : l'étiquette distingue les
    niveaux.
    """

    class Nature(models.TextChoices):
        FORME = "forme", "Forme dessinée"
        IMAGE = "image", "Image importée calée"

    nom = models.CharField("nom", max_length=200)
    etiquette = models.CharField(
        "étiquette",
        max_length=200,
        blank=True,
        help_text="Ex. « Hangar — étage » : distingue les niveaux, "
        "dessinés côte à côte, jamais empilés.",
    )
    nature = models.CharField(
        "nature",
        max_length=10,
        choices=Nature.choices,
        default=Nature.FORME,
    )
    forme = models.JSONField(
        "forme (polygone GeoJSON)",
        null=True,
        blank=True,
        help_text="Polygone tracé à la souris dans l'éditeur (Terra Draw).",
    )
    fichier = models.ImageField(
        "image (PNG/JPG)",
        null=True,
        blank=True,
        upload_to=dossier_plans,
        help_text="Plan numérisé, calé sur l'orthophoto par ses 4 coins.",
    )
    coins = models.JSONField(
        "coins de calage [lng, lat]",
        null=True,
        blank=True,
        help_text="Les 4 coins de l'image en WGS84, posés par "
        "l'éditeur de calage.",
    )
    opacite = models.FloatField(
        "opacité",
        default=0.5,
        blank=True,
        validators=[MinValueValidator(0.1), MaxValueValidator(1.0)],
        help_text="Défaut 50 % (spec technique).",
    )
    couleur = models.CharField(
        "couleur",
        max_length=7,
        default="#3b7dd8",
        blank=True,
        validators=[
            RegexValidator(r"^#[0-9a-fA-F]{6}$", "Couleur au format #rrggbb.")
        ],
    )
    ordre = models.PositiveSmallIntegerField(
        "ordre d'affichage",
        default=0,
        blank=True,
        help_text="Les plans se rangent au-dessus de l'orthophoto, "
        "sous les marqueurs.",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.PROTECT,
        related_name="plans_ajoutes",
    )
    date = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "plan de bâtiment"
        verbose_name_plural = "plans de bâtiments"
        ordering = ["ordre", "nom"]

    def __str__(self):
        if self.etiquette:
            return f"{self.nom} — {self.etiquette}"
        return self.nom

    def donnees_carte(self):
        """Sérialisation pour la carte et les éditeurs (json_script)."""
        return {
            "id": self.pk,
            "nom": self.nom,
            "etiquette": self.etiquette,
            "nature": self.nature,
            "couleur": self.couleur,
            "opacite": self.opacite,
            "ordre": self.ordre,
            "forme": self.forme,
            "coins": self.coins,
            "url": self.fichier.url if self.fichier else None,
        }

    def est_complet(self):
        """La forme est tracée, l'image est calée : le plan apparaît
        sur la carte (sinon il reste « à dessiner » / « à caler »)."""
        if self.nature == self.Nature.FORME:
            return self.forme is not None
        return bool(self.fichier and self.coins)

    def clean(self):
        """Garde-fous : une forme dessinée ne se cale pas ; une image
        calée ne porte pas de forme. Les coins se valident dès qu'ils
        existent — leur absence est un état (« à caler »), pas une
        faute : le calage suit la création."""
        if self.nature == self.Nature.FORME:
            if self.fichier or self.coins:
                raise ValidationError(
                    "Une forme dessinée ne se cale pas : ni image, "
                    "ni coins de calage."
                )
        elif self.nature == self.Nature.IMAGE:
            if self.forme:
                raise ValidationError(
                    "Un plan image ne porte pas de forme dessinée : "
                    "il se cale par ses 4 coins."
                )
            coins = self.coins
            coins_valides = (
                isinstance(coins, list)
                and len(coins) == 4
                and all(
                    isinstance(coin, list)
                    and len(coin) == 2
                    and all(isinstance(v, (int, float)) for v in coin)
                    for coin in coins
                )
            )
            if coins is not None and not coins_valides:
                raise ValidationError(
                    "Une image se cale par exactement 4 coins "
                    "[longitude, latitude] — jamais 3, jamais 5."
                )


class Reglages(models.Model):
    """Réglages du club édités dans l'app (paramètres, animateurs) :
    centre et zoom initiaux de la carte. Une seule ligne ; à la
    première consultation, la valeur de déploiement (.env
    DUDU_CENTRE_CARTE / DUDU_ZOOM_CARTE) sert de valeur initiale —
    ensuite tout se règle depuis la page Paramètres."""

    centre_latitude = models.FloatField("latitude du centre", default=48.42)
    centre_longitude = models.FloatField("longitude du centre", default=-4.55)
    # FloatField : le zoom de MapLibre est décimal (la mini-carte des
    # Paramètres écrit déjà un zoom à une décimale).
    zoom_carte = models.FloatField("zoom de la carte", default=16)

    class Meta:
        verbose_name = "réglages"
        verbose_name_plural = "réglages"

    def __str__(self):
        return "Réglages de la carte"

    @classmethod
    def charge(cls):
        """La ligne unique, créée à la demande depuis le .env."""
        premier = cls.objects.first()
        if premier is not None:
            return premier
        return cls.objects.create(
            centre_latitude=settings.DUDU_CENTRE_CARTE[0],
            centre_longitude=settings.DUDU_CENTRE_CARTE[1],
            zoom_carte=settings.DUDU_ZOOM_CARTE,
        )
