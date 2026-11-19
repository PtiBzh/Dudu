"""Formulaires de Dudu — M1 : postes · M2 : actions · M3 : carte ·
M4 : revues · M5 : photos · M6 : plans de bâtiments.

Le champ satisfaction est absent du formulaire de poste (règle 3 :
seule une revue collégiale l'assigne — un ChangementSatisfaction est
créé par la vue de revue). Depuis M3, la position du poste se choisit
d'un clic sur la mini-carte.

Côté actions : responsable et échéance obligatoires dès la création
(règle 2), motif obligatoire pour abandonner (règle 1). La position
d'une action est optionnelle (elle hérite du poste).
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Action,
    Lieu,
    Photo,
    PlanBatiment,
    Poste,
    Reglages,
    Revue,
    Utilisateur,
    ValeurFrequence,
    ValeurGravite,
    ValeurSatisfaction,
)


class PosteForm(forms.ModelForm):
    """Création/édition d'un poste : la position se saisit d'un clic
    sur la mini-carte (M3), jamais à la main."""

    class Meta:
        model = Poste
        fields = [
            "nom",
            "description",
            "lieu",
            "gravite",
            "frequence",
            "origine",
            "latitude",
            "longitude",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "latitude": forms.HiddenInput(attrs={"class": "coord-lat"}),
            "longitude": forms.HiddenInput(attrs={"class": "coord-lng"}),
        }

    def clean_latitude(self):
        valeur = self.cleaned_data.get("latitude")
        if valeur is not None and not -90 <= valeur <= 90:
            raise ValidationError(
                "La latitude doit rester entre -90 et 90 degrés."
            )
        return valeur

    def clean_longitude(self):
        valeur = self.cleaned_data.get("longitude")
        if valeur is not None and not -180 <= valeur <= 180:
            raise ValidationError(
                "La longitude doit rester entre -180 et 180 degrés."
            )
        return valeur

    def clean(self):
        """Position obligatoire depuis M3. Tolérance : l'édition d'un
        ancien poste jamais positionné ne l'exige pas tant qu'on n'y
        touche pas (données antérieures à la carte)."""
        donnees = super().clean()
        ancien_jamais_positionne = (
            self.instance.pk is not None and self.instance.latitude is None
        )
        if donnees.get("latitude") is None or donnees.get("longitude") is None:
            if not ancien_jamais_positionne:
                self.add_error(
                    None,
                    "Position obligatoire : clique sur la carte pour placer "
                    "le poste.",
                )
        return donnees


class ActionCreationForm(forms.ModelForm):
    """Création d'une action : responsable et échéance obligatoires
    (règle 2), statut à « à faire » d'office, position optionnelle
    (elle hérite du poste si laissée vide)."""

    class Meta:
        model = Action
        fields = [
            "intitule",
            "description",
            "responsable",
            "echeance",
            "latitude",
            "longitude",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "echeance": forms.DateInput(attrs={"type": "date"}),
            "latitude": forms.HiddenInput(attrs={"class": "coord-lat"}),
            "longitude": forms.HiddenInput(attrs={"class": "coord-lng"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = Utilisateur.objects.filter(
            is_active=True
        )

    def clean_latitude(self):
        valeur = self.cleaned_data.get("latitude")
        if valeur is not None and not -90 <= valeur <= 90:
            raise ValidationError(
                "La latitude doit rester entre -90 et 90 degrés."
            )
        return valeur

    def clean_longitude(self):
        valeur = self.cleaned_data.get("longitude")
        if valeur is not None and not -180 <= valeur <= 180:
            raise ValidationError(
                "La longitude doit rester entre -180 et 180 degrés."
            )
        return valeur


class ActionModificationForm(ActionCreationForm):
    """Édition : échéance décalable, statut modifiable, motif
    obligatoire pour abandonner."""

    class Meta(ActionCreationForm.Meta):
        fields = ActionCreationForm.Meta.fields + ["statut", "motif_abandon"]
        widgets = {
            **ActionCreationForm.Meta.widgets,
            "motif_abandon": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        donnees = super().clean()
        if (
            donnees.get("statut") == Action.Statut.ABANDONNEE
            and not donnees.get("motif_abandon")
        ):
            self.add_error(
                "motif_abandon",
                "Un motif est obligatoire pour abandonner une action.",
            )
        return donnees


class RevueForm(forms.ModelForm):
    """Création/édition d'une revue : date, participants, compte
    rendu. Les postes examinés se choisissent sur la page de la revue
    — c'est là que se prennent et se consignent les décisions."""

    class Meta:
        model = Revue
        fields = ["date", "participants", "compte_rendu"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "participants": forms.CheckboxSelectMultiple,
            "compte_rendu": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].queryset = (
            Utilisateur.objects.filter(is_active=True)
        )
        self.fields["date"].initial = timezone.localdate


class PhotoForm(forms.ModelForm):
    """Téléversement d'une photo (avant ou après) : seul le fichier
    se choisit ici — le type et le rattachement viennent de la vue,
    jamais de la requête."""

    class Meta:
        model = Photo
        fields = ["fichier"]
        widgets = {
            "fichier": forms.FileInput(attrs={"accept": "image/*"}),
        }


class PlanForm(forms.ModelForm):
    """Création/édition d'un plan de bâtiment. Le dessin (Terra Draw)
    et le calage (4 coins) se font dans les éditeurs dédiés, pas
    ici."""

    class Meta:
        model = PlanBatiment
        fields = [
            "nom",
            "etiquette",
            "nature",
            "couleur",
            "ordre",
            "opacite",
            "fichier",
        ]
        widgets = {
            "etiquette": forms.TextInput(
                attrs={"placeholder": "Ex. Hangar — étage"}
            ),
            "couleur": forms.TextInput(attrs={"type": "color"}),
            "ordre": forms.NumberInput(attrs={"min": 0}),
            "opacite": forms.NumberInput(
                attrs={"min": "0.1", "max": "1", "step": "0.05"}
            ),
            "fichier": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean(self):
        """Nature « image » : le fichier est requis, dès la création
        comme au remplacement (le calage suivra)."""
        donnees = super().clean()
        if donnees.get("nature") == PlanBatiment.Nature.IMAGE:
            fichier = donnees.get("fichier") or self.instance.fichier
            if not fichier:
                self.add_error(
                    "fichier",
                    "Importe une image (PNG/JPG) : elle se calera sur "
                    "l'orthophoto par ses 4 coins.",
                )
        return donnees


# Équipe (M8) -----------------------------------------------------------------


class UtilisateurCreationForm(forms.Form):
    """Nouveau compte : identifiant, nom, mot de passe saisi une fois
    (petite équipe ; la personne le change ensuite si besoin)."""

    username = forms.CharField(label="Identifiant", max_length=150)
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    mot_de_passe = forms.CharField(
        label="Mot de passe", min_length=8, widget=forms.PasswordInput
    )
    is_animateur = forms.BooleanField(
        label="Animateur (gère l'équipe et les paramètres)", required=False
    )

    def clean_username(self):
        identifiant = self.cleaned_data["username"]
        if Utilisateur.objects.filter(username__iexact=identifiant).exists():
            raise ValidationError("Cet identifiant est déjà pris.")
        return identifiant

    def save(self):
        return Utilisateur.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["mot_de_passe"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            is_animateur=self.cleaned_data["is_animateur"],
        )


class UtilisateurModificationForm(forms.ModelForm):
    """Édition d'un compte : rôle, activation, et un nouveau mot de
    passe laissé vide pour ne rien changer."""

    nouveau_mot_de_passe = forms.CharField(
        label="Nouveau mot de passe (vide = inchangé)",
        min_length=8,
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Utilisateur
        fields = ["username", "first_name", "last_name", "is_animateur", "is_active"]

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        mot = self.cleaned_data.get("nouveau_mot_de_passe")
        if mot:
            utilisateur.set_password(mot)
        if commit:
            utilisateur.save()
        return utilisateur


# Paramètres (M8) --------------------------------------------------------------


class LieuForm(forms.ModelForm):
    class Meta:
        model = Lieu
        fields = ["nom", "ordre"]


class ValeurCotationForm(forms.ModelForm):
    """Socle des listes cotées (gravités, fréquences, satisfactions),
    champs identiques : libellé, ordre, couleur du marqueur carte."""

    class Meta:
        fields = ["libelle", "ordre", "couleur"]
        widgets = {"couleur": forms.TextInput(attrs={"placeholder": "#0d6b7c"})}


class ValeurGraviteForm(ValeurCotationForm):
    class Meta(ValeurCotationForm.Meta):
        model = ValeurGravite


class ValeurFrequenceForm(ValeurCotationForm):
    class Meta(ValeurCotationForm.Meta):
        model = ValeurFrequence


class ValeurSatisfactionForm(ValeurCotationForm):
    class Meta(ValeurCotationForm.Meta):
        model = ValeurSatisfaction


class ReglagesForm(forms.ModelForm):
    """Centre et zoom initiaux de la carte du club."""

    class Meta:
        model = Reglages
        fields = ["centre_latitude", "centre_longitude", "zoom_carte"]

    def clean_centre_latitude(self):
        valeur = self.cleaned_data["centre_latitude"]
        if not -90 <= valeur <= 90:
            raise ValidationError("La latitude doit rester entre -90 et 90 degrés.")
        return valeur

    def clean_centre_longitude(self):
        valeur = self.cleaned_data["centre_longitude"]
        if not -180 <= valeur <= 180:
            raise ValidationError("La longitude doit rester entre -180 et 180 degrés.")
        return valeur

    def clean_zoom_carte(self):
        valeur = self.cleaned_data["zoom_carte"]
        if not 2 <= valeur <= 19:
            raise ValidationError("Le zoom doit rester entre 2 et 19.")
        return valeur
