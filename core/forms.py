"""Formulaires de Dudu — M1 : postes · M2 : actions · M3 : carte ·
M4 : revues.

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

from .models import Action, Poste, Revue, Utilisateur


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
