"""Vues de Dudu — M0 : accueil (tableau de bord vide)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Tableau de bord. Les compteurs (postes, actions, retards)
    arrivent avec M1, M2 et M4."""
    return render(request, "core/home.html", {"section": "accueil"})
