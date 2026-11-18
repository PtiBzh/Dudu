"""Formulaires de Dudu — M1 : postes · M2 : actions.

Le champ satisfaction est volontairement absent (règle 3 : seul
une revue collégiale l'assigne — M4). La position carte est
optionnelle ici, obligatoire au clic près de la carte en M3.

Côté actions : responsable et échéance obligatoires dès la création
(règle 2), motif obligatoire pour abandonner (règle 1).
"""
from django import forms

from .models import Action, Poste, Utilisateur


class PosteForm(forms.ModelForm):
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
            "latitude": forms.NumberInput(attrs={"step": "any"}),
            "longitude": forms.NumberInput(attrs={"step": "any"}),
        }


class ActionCreationForm(forms.ModelForm):
    """Création d'une action : responsable et échéance obligatoires
    (règle 2), statut à « à faire » d'office."""

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
            "latitude": forms.NumberInput(attrs={"step": "any"}),
            "longitude": forms.NumberInput(attrs={"step": "any"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = Utilisateur.objects.filter(
            is_active=True
        )


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
