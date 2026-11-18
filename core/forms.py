"""Formulaires de Dudu — M1 : formulaire de poste.

Le champ satisfaction est volontairement absent (règle 3 : seul
une revue collégiale l'assigne — M4). La position carte est
optionnelle ici, obligatoire au clic près de la carte en M3.
"""
from django import forms

from .models import Poste


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
