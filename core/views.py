"""Vues de Dudu — M1 : accueil, postes.

Rappels de spec : la création d'un poste est libre (équipe identifiée),
l'édition est réservée à l'auteur et à l'animateur (tracée), la
satisfaction ne se change qu'en revue (M4) — le formulaire ne la propose
donc pas.
"""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PosteForm
from .models import Lieu, Poste, ValeurGravite, ValeurSatisfaction


@login_required
def home(request):
    """Tableau de bord : compteurs des postes (M1)."""
    context = {
        "section": "accueil",
        "postes_actifs": Poste.objects.filter(archive=False).count(),
        "postes_archives": Poste.objects.filter(archive=True).count(),
        "cotation_attention": Poste.objects.filter(
            archive=False, gravite__isnull=False
        ).count(),
    }
    return render(request, "core/home.html", context)


@login_required
def postes(request):
    """Liste des postes avec filtres : lieu, satisfaction, gravité,
    recherche texte, et état d'archivage."""
    liste = Poste.objects.select_related(
        "lieu", "auteur", "gravite", "frequence", "satisfaction"
    )

    archivage = request.GET.get("archivage", "actifs")
    if archivage == "archives":
        liste = liste.filter(archive=True)
    elif archivage != "tous":
        liste = liste.filter(archive=False)

    filtres = {}
    for champ in ("lieu", "satisfaction", "gravite"):
        valeur = request.GET.get(champ, "")
        if valeur:
            liste = liste.filter(**{f"{champ}_id": valeur})
            filtres[champ] = valeur

    recherche = request.GET.get("q", "").strip()
    if recherche:
        liste = liste.filter(
            Q(nom__icontains=recherche)
            | Q(description__icontains=recherche)
        )
        filtres["q"] = recherche

    context = {
        "section": "postes",
        "postes": liste,
        "lieux": Lieu.objects.all(),
        "satisfactions": ValeurSatisfaction.objects.all(),
        "gravites": ValeurGravite.objects.all(),
        "filtres": filtres,
        "archivage": archivage,
    }
    return render(request, "core/poste_liste.html", context)


@login_required
def poste_detail(request, pk):
    poste = get_object_or_404(
        Poste.objects.select_related(
            "lieu", "auteur", "gravite", "frequence", "satisfaction"
        ),
        pk=pk,
    )
    return render(
        request,
        "core/poste_detail.html",
        {
            "section": "postes",
            "poste": poste,
            "modifiable": poste.peut_etre_modifie_par(request.user),
        },
    )


@login_required
def poste_creer(request):
    """Création libre pour toute l'équipe (règle 4)."""
    form = PosteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        poste = form.save(commit=False)
        poste.auteur = request.user
        poste.save()
        return redirect("poste_detail", pk=poste.pk)
    return render(
        request,
        "core/poste_form.html",
        {"section": "postes", "form": form, "titre": "Nouveau poste"},
    )


@login_required
def poste_modifier(request, pk):
    poste = get_object_or_404(Poste, pk=pk)
    if not poste.peut_etre_modifie_par(request.user):
        raise PermissionDenied("Seul l'auteur ou l'animateur peut modifier un poste.")
    form = PosteForm(request.POST or None, instance=poste)
    if request.method == "POST" and form.is_valid():
        form.save()
        poste.editions.create(qui=request.user)  # trace « modifiée par X le Y »
        return redirect("poste_detail", pk=poste.pk)
    return render(
        request,
        "core/poste_form.html",
        {
            "section": "postes",
            "form": form,
            "titre": "Modifier le poste",
            "poste": poste,
        },
    )


@login_required
def poste_archiver(request, pk):
    """Règle 1 : on n'efface jamais un poste, on l'archive."""
    poste = get_object_or_404(Poste, pk=pk)
    if not poste.peut_etre_modifie_par(request.user):
        raise PermissionDenied("Seul l'auteur ou l'animateur peut archiver un poste.")
    if request.method == "POST":
        poste.archive = not poste.archive
        poste.save()
    return redirect("poste_detail", pk=poste.pk)
