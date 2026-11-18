"""Vues de Dudu — M1 : postes · M2 : actions · M3 : carte.

Rappels de spec : la création d'un poste est libre (équipe identifiée),
l'édition est réservée à l'auteur et à l'animateur (tracée), la
satisfaction ne se change qu'en revue (M4). Une action exige
responsable et échéance (règle 2) ; hors revue, sa création est
réservée à l'animateur (règle 5). Depuis M3, la carte partage les
filtres de la liste des postes et la position y est obligatoire.
"""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import ActionCreationForm, ActionModificationForm, PosteForm
from .models import (
    Action,
    Lieu,
    Poste,
    Utilisateur,
    ValeurGravite,
    ValeurSatisfaction,
)

STATUTS_OUVERTS = [Action.Statut.A_FAIRE, Action.Statut.EN_COURS]


@login_required
def home(request):
    """Tableau de bord : compteurs des postes et des actions."""
    context = {
        "section": "accueil",
        "postes_actifs": Poste.objects.filter(archive=False).count(),
        "postes_archives": Poste.objects.filter(archive=True).count(),
        "cotation_attention": Poste.objects.filter(
            archive=False, gravite__isnull=False
        ).count(),
        "actions_ouvertes": Action.objects.filter(
            statut__in=STATUTS_OUVERTS
        ).count(),
        "actions_en_retard": Action.objects.filter(
            statut__in=STATUTS_OUVERTS, echeance__lt=timezone.localdate()
        ).count(),
    }
    return render(request, "core/home.html", context)


@login_required
def carte(request):
    """Carte des postes et actions (M3) — mêmes filtres que la liste.

    Fond : orthophoto IGN via la géoplateforme (tuiles WMTS chargées
    côté navigateur par MapLibre). Seuls les postes positionnés sont
    affichés ; les actions ouvertes liées à ces postes apparaissent en
    petits points. Un clic sur un marqueur ouvre un lien vers la
    fiche ; ?poste=pk centre la vue sur un poste donné.
    """
    liste = Poste.objects.filter(latitude__isnull=False).select_related(
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

    actions_visibles = Action.objects.filter(
        latitude__isnull=False,
        statut__in=STATUTS_OUVERTS,
        poste__in=liste.values("pk"),
    ).select_related("poste")

    donnees_carte = {
        "postes": [
            {
                "id": poste.pk,
                "nom": poste.nom,
                "lat": poste.latitude,
                "lng": poste.longitude,
                "couleur": poste.gravite.couleur if poste.gravite else None,
                "halo": (
                    poste.satisfaction.couleur
                    if poste.satisfaction
                    else None
                ),
                "url": reverse("poste_detail", args=[poste.pk]),
            }
            for poste in liste
        ],
        "actions": [
            {
                "id": action.pk,
                "intitule": action.intitule,
                "statut": action.get_statut_display(),
                "lat": action.latitude,
                "lng": action.longitude,
                "url": reverse("action_detail", args=[action.pk]),
            }
            for action in actions_visibles
        ],
    }
    context = {
        "section": "carte",
        "donnees_carte": donnees_carte,
        "centre": settings.DUDU_CENTRE_CARTE,
        "zoom": settings.DUDU_ZOOM_CARTE,
        "poste_cible": request.GET.get("poste", ""),
        "filtres": filtres,
        "archivage": archivage,
        "lieux": Lieu.objects.all(),
        "satisfactions": ValeurSatisfaction.objects.all(),
        "gravites": ValeurGravite.objects.all(),
    }
    return render(request, "core/carte.html", context)


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
        {
            "section": "postes",
            "form": form,
            "titre": "Nouveau poste",
            "centre": settings.DUDU_CENTRE_CARTE,
            "zoom": settings.DUDU_ZOOM_CARTE,
        },
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
            "centre": settings.DUDU_CENTRE_CARTE,
            "zoom": settings.DUDU_ZOOM_CARTE,
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


@login_required
def actions(request):
    """Liste des actions : par responsable, par statut, retards en
    évidence (écran 4 de la spec technique)."""
    liste = Action.objects.select_related(
        "poste", "responsable"
    ).order_by("echeance", "date_creation")

    statut = request.GET.get("statut", "ouvertes")
    if statut == "ouvertes":
        liste = liste.filter(statut__in=STATUTS_OUVERTS)
    elif statut in Action.Statut.values:
        liste = liste.filter(statut=statut)

    responsable = request.GET.get("responsable", "")
    if responsable:
        liste = liste.filter(responsable_id=responsable)

    retard = request.GET.get("retard", "")
    if retard:
        liste = liste.filter(
            statut__in=STATUTS_OUVERTS, echeance__lt=timezone.localdate()
        )

    recherche = request.GET.get("q", "").strip()
    if recherche:
        liste = liste.filter(
            Q(intitule__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    context = {
        "section": "actions",
        "actions": liste,
        "statuts": Action.Statut.choices,
        "equipe": Utilisateur.objects.filter(is_active=True),
        "statut_selection": statut,
        "responsable_selection": responsable,
        "retard_selection": bool(retard),
        "q_visuel": recherche,
    }
    return render(request, "core/action_liste.html", context)


@login_required
def action_detail(request, pk):
    action = get_object_or_404(
        Action.objects.select_related("poste", "responsable", "poste__lieu"),
        pk=pk,
    )
    return render(
        request,
        "core/action_detail.html",
        {
            "section": "actions",
            "action": action,
            "modifiable": action.peut_etre_modifiee_par(request.user),
        },
    )


@login_required
def action_creer(request, poste_pk):
    """Règle 5 : hors revue (les revues arrivent en M4), seule
    l'animatrice ou l'animateur crée une action urgente. L'action est
    alors inscrite d'office à la prochaine revue."""
    poste = get_object_or_404(Poste, pk=poste_pk)
    if not request.user.is_animateur:
        raise PermissionDenied(
            "Jusqu'aux revues (M4), seule l'animatrice ou l'animateur "
            "peut créer une action (règle 5)."
        )
    form = ActionCreationForm(
        request.POST or None,
        initial={"latitude": poste.latitude, "longitude": poste.longitude},
    )
    if request.method == "POST" and form.is_valid():
        action = form.save(commit=False)
        action.poste = poste
        # Position héritée du poste si aucune autre n'est donnée.
        if action.latitude is None:
            action.latitude = poste.latitude
        if action.longitude is None:
            action.longitude = poste.longitude
        action.save()
        return redirect("action_detail", pk=action.pk)
    return render(
        request,
        "core/action_form.html",
        {
            "section": "actions",
            "form": form,
            "titre": "Nouvelle action",
            "poste": poste,
            "centre": settings.DUDU_CENTRE_CARTE,
            "zoom": settings.DUDU_ZOOM_CARTE,
        },
    )


@login_required
def action_modifier(request, pk):
    action = get_object_or_404(
        Action.objects.select_related("poste"), pk=pk
    )
    if not action.peut_etre_modifiee_par(request.user):
        raise PermissionDenied(
            "Seul le responsable ou l'animateur peut modifier une action."
        )
    form = ActionModificationForm(request.POST or None, instance=action)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("action_detail", pk=action.pk)
    return render(
        request,
        "core/action_form.html",
        {
            "section": "actions",
            "form": form,
            "titre": "Modifier l'action",
            "action": action,
            "poste": action.poste,
            "centre": settings.DUDU_CENTRE_CARTE,
            "zoom": settings.DUDU_ZOOM_CARTE,
        },
    )
