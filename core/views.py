"""Vues de Dudu — M1 : postes · M2 : actions · M3 : carte · M4 : revues ·
M5 : photos avant/après · M6 : plans de bâtiments.

Rappels de spec : la création d'un poste est libre (équipe identifiée),
l'édition est réservée à l'auteur et à l'animateur (tracée), la
satisfaction ne se change qu'en revue (M4). Une action exige
responsable et échéance (règle 2) ; hors revue, sa création est
réservée à l'animateur (règle 5), au sein d'une revue elle est
collégiale. Depuis M3, la carte partage les filtres de la liste des
postes et la position y est obligatoire. Les plans de bâtiments (M6)
se dessinent et se calent côté admin : équipe de secrétariat (staff).
"""
import json
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .fichiers import compresser_photo
from .forms import (
    ActionCreationForm,
    ActionModificationForm,
    PhotoForm,
    PlanForm,
    PosteForm,
    RevueForm,
)
from .models import (
    Action,
    ChangementSatisfaction,
    Lieu,
    Photo,
    PlanBatiment,
    Poste,
    Revue,
    Utilisateur,
    ValeurGravite,
    ValeurSatisfaction,
)

STATUTS_OUVERTS = [Action.Statut.A_FAIRE, Action.Statut.EN_COURS]


def staff_seulement(vue):
    """Écran 6 : les plans de bâtiments se dessinent et se calent côté
    admin — réservé à l'équipe de secrétariat (staff)."""

    @wraps(vue)
    def interne(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Les plans de bâtiments se gèrent côté admin "
                "(équipe de secrétariat)."
            )
        return vue(request, *args, **kwargs)

    return interne


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
        "repartition": ValeurSatisfaction.objects.annotate(
            nb=Count("postes", filter=Q(postes__archive=False))
        ),
        "derniere_revue": Revue.objects.order_by(
            "-date", "-date_creation"
        ).first(),
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
        "plans": [plan.donnees_carte() for plan in PlanBatiment.objects.all()],
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
    photos_avant = poste.photos_avant.all()
    paires = [
        {
            "action": action,
            "photo_avant": photos_avant[0] if photos_avant else None,
            "photo_apres": action.photos_apres.first(),
        }
        for action in poste.actions.filter(
            statut=Action.Statut.FAITE, photos_apres__isnull=False
        ).distinct().order_by("-date_cloture", "-date_creation")
    ]
    return render(
        request,
        "core/poste_detail.html",
        {
            "section": "postes",
            "poste": poste,
            "modifiable": poste.peut_etre_modifie_par(request.user),
            "photos_avant": photos_avant,
            "paires": paires,
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
    """Règle 2 : responsable et échéance obligatoires. Règle 5 : hors
    revue, la création est réservée à l'animateur (action urgente,
    inscrite d'office à la prochaine revue). Au sein d'une revue
    collégiale (M4), toute l'équipe identifiée peut saisir la décision
    du moment — l'action porte alors la trace de cette revue."""
    poste = get_object_or_404(Poste, pk=poste_pk)

    revue = None
    identifiant_revue = request.GET.get("revue") or request.POST.get("revue")
    if identifiant_revue:
        # Une revue précisée doit exister : pas de rattachement fantôme.
        revue = get_object_or_404(Revue, pk=identifiant_revue)
    elif not request.user.is_animateur:
        raise PermissionDenied(
            "Hors revue, seule l'animatrice ou l'animateur peut créer "
            "une action urgente (règle 5)."
        )

    form = ActionCreationForm(
        request.POST or None,
        initial={"latitude": poste.latitude, "longitude": poste.longitude},
    )
    if request.method == "POST" and form.is_valid():
        action = form.save(commit=False)
        action.poste = poste
        action.revue = revue
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
            "revue": revue,
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
        # Règle 5 des écrans (spec technique) : clôturer sans photo
        # « après » se signale, sans jamais bloquer.
        if (
            action.statut == Action.Statut.FAITE
            and not action.photos_apres.exists()
        ):
            messages.warning(
                request,
                "Action clôturée sans photo « après » : ajoute-la, "
                "elle témoigne du travail accompli.",
            )
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


@login_required
def poste_photo_ajouter(request, poste_pk):
    """Photo « avant » : documenter la situation constatée. Création
    libre, à l'image des postes (règle 4) ; compression à l'upload."""
    poste = get_object_or_404(Poste, pk=poste_pk)
    if request.method == "POST":
        formulaire = PhotoForm(request.POST, request.FILES)
        if formulaire.is_valid():
            photo = formulaire.save(commit=False)
            photo.type = Photo.Type.AVANT
            photo.poste = poste
            photo.auteur = request.user
            photo.fichier = compresser_photo(request.FILES["fichier"])
            photo.save()
        else:
            messages.error(
                request, "Fichier manquant ou pas une image exploitable."
            )
    return redirect("poste_detail", pk=poste.pk)


@login_required
def action_photo_ajouter(request, pk):
    """Photo « après » : témoigner du travail accompli. Réservée au
    responsable ou à l'animateur, comme l'édition de l'action."""
    action = get_object_or_404(Action, pk=pk)
    if not action.peut_etre_modifiee_par(request.user):
        raise PermissionDenied(
            "Seul le responsable ou l'animateur ajoute la photo "
            "« après » d'une action."
        )
    if request.method == "POST":
        formulaire = PhotoForm(request.POST, request.FILES)
        if formulaire.is_valid():
            photo = formulaire.save(commit=False)
            photo.type = Photo.Type.APRES
            photo.action = action
            photo.auteur = request.user
            photo.fichier = compresser_photo(request.FILES["fichier"])
            photo.save()
        else:
            messages.error(
                request, "Fichier manquant ou pas une image exploitable."
            )
    return redirect("action_detail", pk=action.pk)


@login_required
def revues(request):
    """Journal historique : toutes les revues, de la plus récente à
    la plus ancienne."""
    liste = Revue.objects.prefetch_related("participants", "postes")
    return render(
        request,
        "core/revue_liste.html",
        {"section": "revues", "revues": liste},
    )


@login_required
def revue_creer(request):
    """Une revue s'ouvre par quiconque de l'équipe anime la réunion :
    le secrétariat de l'app ne connaît pas de gatekeeper."""
    form = RevueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        revue = form.save()
        return redirect("revue_detail", pk=revue.pk)
    return render(
        request,
        "core/revue_form.html",
        {"section": "revues", "form": form, "titre": "Nouvelle revue"},
    )


@login_required
def revue_modifier(request, pk):
    revue = get_object_or_404(Revue, pk=pk)
    form = RevueForm(request.POST or None, instance=revue)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("revue_detail", pk=revue.pk)
    return render(
        request,
        "core/revue_form.html",
        {
            "section": "revues",
            "form": form,
            "titre": "Modifier la revue",
            "revue": revue,
        },
    )


@login_required
def revue_detail(request, pk):
    """Écran de travail de la revue (écran 5 de la spec) : postes
    examinés, décisions de satisfaction journalisées, actions créées,
    compte rendu."""
    revue = get_object_or_404(
        Revue.objects.prefetch_related(
            "participants",
            "postes",
            "postes__gravite",
            "postes__satisfaction",
        ),
        pk=pk,
    )
    # Actions clôturées depuis la revue précédente (écran 5) : c'est
    # ici que l'avant/après témoigne du chemin parcouru.
    precedente = Revue.objects.filter(date__lt=revue.date).order_by(
        "-date", "-date_creation"
    ).first()
    cloturees = Action.objects.filter(statut=Action.Statut.FAITE).order_by(
        "-date_cloture", "-date_creation"
    )
    if precedente:
        cloturees = cloturees.filter(date_cloture__date__gte=precedente.date)
    cloturees = cloturees.select_related("poste")
    paires_cloturees = [
        {
            "action": action,
            "photo_avant": action.poste.photos_avant.first(),
            "photo_apres": action.photos_apres.first(),
        }
        for action in cloturees
    ]
    context = {
        "section": "revues",
        "revue": revue,
        "postes_examines": revue.postes.all(),
        "postes_disponibles": Poste.objects.filter(archive=False)
        .exclude(revues=revue)
        .order_by("nom"),
        "satisfactions": ValeurSatisfaction.objects.all(),
        "changements": revue.changements.select_related(
            "poste", "ancienne", "nouvelle"
        ),
        "actions": revue.actions.select_related("poste", "responsable"),
        "paires_cloturees": paires_cloturees,
    }
    return render(request, "core/revue_detail.html", context)


@login_required
def revue_poste_ajouter(request, pk):
    """Ajoute un poste aux postes examinés (POST uniquement)."""
    revue = get_object_or_404(Revue, pk=pk)
    if request.method == "POST":
        poste = get_object_or_404(
            Poste, pk=request.POST.get("poste", ""), archive=False
        )
        revue.postes.add(poste)
    return redirect("revue_detail", pk=revue.pk)


@login_required
def revue_poste_retirer(request, pk, poste_pk):
    """Retire un poste des examinés (POST uniquement). Les décisions
    déjà consignées restent au journal — elles restent vraies."""
    revue = get_object_or_404(Revue, pk=pk)
    if request.method == "POST":
        poste = get_object_or_404(Poste, pk=poste_pk)
        if poste in revue.postes.all():
            revue.postes.remove(poste)
    return redirect("revue_detail", pk=revue.pk)


@login_required
def revue_satisfaction(request, pk, poste_pk):
    """Règle 3 : la satisfaction d'un poste ne change qu'ici — décision
    collégiale consignée au journal (POST uniquement, poste examiné
    uniquement, nouvelle valeur distincte de l'actuelle uniquement)."""
    revue = get_object_or_404(Revue, pk=pk)
    poste = get_object_or_404(revue.postes, pk=poste_pk)
    if request.method == "POST":
        nouvelle = get_object_or_404(
            ValeurSatisfaction, pk=request.POST.get("satisfaction", "")
        )
        if nouvelle != poste.satisfaction:
            ChangementSatisfaction.objects.create(
                revue=revue,
                poste=poste,
                ancienne=poste.satisfaction,
                nouvelle=nouvelle,
            )
            poste.satisfaction = nouvelle
            poste.save(update_fields=["satisfaction"])
    retour = reverse("revue_detail", args=[revue.pk])
    return redirect(f"{retour}#poste-{poste.pk}")


@login_required
def medias(request, chemin):
    """Sert les médias du volume /data — identifiés, jamais publics
    (spéc « aucune exposition publique », M7). Gunicorn + WhiteNoise
    prend en charge les statiques ; les médias (photos, plans) eux
    restent derrière une session. Garde-fou d'évasion de chemin."""
    racine = Path(settings.MEDIA_ROOT).resolve()
    cible = (racine / chemin).resolve()
    try:
        cible.relative_to(racine)
    except ValueError:
        raise Http404("Média introuvable.")
    if not cible.is_file():
        raise Http404("Média introuvable.")
    return FileResponse(cible.open("rb"))


def centre_de_coins(coins):
    """Centre d'un jeu de 4 coins [lng, lat] — pour cadrer l'éditeur
    de calage sur l'image."""
    if not coins:
        return settings.DUDU_CENTRE_CARTE
    lats = [coin[1] for coin in coins]
    lngs = [coin[0] for coin in coins]
    return (sum(lats) / len(lats), sum(lngs) / len(lngs))


@login_required
@staff_seulement
def plans(request):
    """Écran 6 : les plans de bâtiments du club, dessinés ou calés."""
    liste = PlanBatiment.objects.select_related("auteur").all()
    return render(
        request,
        "core/plan_liste.html",
        {"section": "plans", "plans": liste},
    )


@login_required
@staff_seulement
def plan_nouveau(request):
    """Création d'un plan. La nature oriente vers l'éditeur adéquat :
    dessin (Terra Draw) ou calage d'image."""
    if request.method == "POST":
        formulaire = PlanForm(request.POST, request.FILES)
        if formulaire.is_valid():
            plan = formulaire.save(commit=False)
            plan.auteur = request.user
            plan.save()
            messages.success(request, "Plan enregistré.")
            if plan.nature == PlanBatiment.Nature.IMAGE:
                return redirect("plan_calage", pk=plan.pk)
            return redirect("plan_dessin", pk=plan.pk)
        messages.error(
            request, "Le plan n'est pas enregistré : vérifie le formulaire."
        )
    else:
        formulaire = PlanForm()
    return render(
        request,
        "core/plan_form.html",
        {"section": "plans", "titre": "Nouveau plan", "formulaire": formulaire},
    )


@login_required
@staff_seulement
def plan_modifier(request, pk):
    """Édition des attributs d'un plan (nom, couleur, ordre…)."""
    plan = get_object_or_404(PlanBatiment, pk=pk)
    if request.method == "POST":
        formulaire = PlanForm(request.POST, request.FILES, instance=plan)
        if formulaire.is_valid():
            formulaire.save()
            messages.success(request, "Plan modifié.")
            return redirect("plans")
        messages.error(
            request, "Le plan n'est pas enregistré : vérifie le formulaire."
        )
    else:
        formulaire = PlanForm(instance=plan)
    return render(
        request,
        "core/plan_form.html",
        {
            "section": "plans",
            "titre": f"Modifier « {plan} »",
            "formulaire": formulaire,
            "plan": plan,
        },
    )


@login_required
@staff_seulement
def plan_supprimer(request, pk):
    """Suppression d'un plan (et de son fichier) : un plan de
    bâtiment est du contexte de travail, pas une trace d'amélioration
    — effacer un import erroné reste légitime (POST uniquement)."""
    plan = get_object_or_404(PlanBatiment, pk=pk)
    if request.method == "POST":
        if plan.fichier:
            plan.fichier.delete(save=False)
        plan.delete()
        messages.success(request, f"Plan « {plan} » supprimé.")
    return redirect("plans")


def forme_valide(forme):
    """Un polygone GeoJSON lisible, avec au moins un anneau fermé."""
    return (
        isinstance(forme, dict)
        and forme.get("type") == "Polygon"
        and isinstance(forme.get("coordinates"), list)
        and len(forme["coordinates"]) > 0
    )


@login_required
@staff_seulement
def plan_dessin(request, pk):
    """Éditeur de dessin (Terra Draw) : trace le polygone du plan sur
    l'orthophoto. La forme sauvegardée s'affiche en relecture, le
    nouveau tracé l'écrase à l'enregistrement."""
    plan = get_object_or_404(PlanBatiment, pk=pk)
    if plan.nature != PlanBatiment.Nature.FORME:
        raise PermissionDenied(
            "Seul un plan « forme dessinée » se trace à la souris ; "
            "un plan image se cale."
        )
    if request.method == "POST":
        try:
            forme = json.loads(request.POST.get("forme", ""))
        except (json.JSONDecodeError, TypeError):
            forme = None
        if forme_valide(forme):
            plan.forme = forme
            plan.save(update_fields=["forme"])
            messages.success(
                request,
                "Forme enregistrée : le plan apparaît sur la carte.",
            )
            return redirect("plans")
        messages.error(
            request,
            "Forme illisible : trace le polygone puis enregistre.",
        )
    zoom = settings.DUDU_ZOOM_CARTE if not plan.forme else 18
    donnees_dessin = {
        "lat": settings.DUDU_CENTRE_CARTE[0],
        "lng": settings.DUDU_CENTRE_CARTE[1],
        "zoom": zoom,
        "couleur": plan.couleur,
        "forme": plan.forme,
    }
    if plan.forme:
        latitude, longitude = centre_de_coins(plan.forme["coordinates"][0])
        donnees_dessin["lat"] = latitude
        donnees_dessin["lng"] = longitude
    return render(
        request,
        "core/plan_dessin.html",
        {
            "section": "plans",
            "plan": plan,
            "donnees_dessin": donnees_dessin,
        },
    )


@login_required
@staff_seulement
def plan_calage(request, pk):
    """Éditeur de calage maison : l'image se déplace à la souris, ses
    4 poignées de coin se tirent sur les repères du terrain, l'échelle
    et l'opacité se règlent (spec technique, ~150 lignes de JS)."""
    plan = get_object_or_404(PlanBatiment, pk=pk)
    if plan.nature != PlanBatiment.Nature.IMAGE:
        raise PermissionDenied(
            "Seul un plan image se cale ; un plan forme se trace à "
            "la souris."
        )
    if request.method == "POST":
        try:
            coins = json.loads(request.POST.get("coins", ""))
        except (json.JSONDecodeError, TypeError):
            coins = None
        try:
            opacite = float(request.POST.get("opacite", plan.opacite))
        except ValueError:
            opacite = plan.opacite
        coins_valides = (
            isinstance(coins, list)
            and len(coins) == 4
            and all(
                isinstance(coin, list)
                and len(coin) == 2
                and all(isinstance(v, (int, float)) for v in coin)
                for coin in coins
            )
            and 0.1 <= opacite <= 1
        )
        if coins_valides:
            plan.coins = coins
            plan.opacite = opacite
            plan.save(update_fields=["coins", "opacite"])
            messages.success(
                request,
                "Calage enregistré : le plan apparaît sur la carte.",
            )
            return redirect("plans")
        messages.error(
            request, "Calage illisible : 4 coins sur la carte, puis "
            "enregistre."
        )
    lat, lng = settings.DUDU_CENTRE_CARTE
    coins = plan.coins or [
        [lng - 0.0004, lat + 0.0003],
        [lng + 0.0004, lat + 0.0003],
        [lng + 0.0004, lat - 0.0003],
        [lng - 0.0004, lat - 0.0003],
    ]
    latitude, longitude = centre_de_coins(coins)
    donnees_calage = {
        "lat": latitude,
        "lng": longitude,
        "zoom": settings.DUDU_ZOOM_CARTE,
        "url": plan.fichier.url if plan.fichier else None,
        "coins": coins,
        "opacite": plan.opacite,
        "couleur": plan.couleur,
    }
    return render(
        request,
        "core/plan_calage.html",
        {
            "section": "plans",
            "plan": plan,
            "donnees_calage": donnees_calage,
        },
    )
