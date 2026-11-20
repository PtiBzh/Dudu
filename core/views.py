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
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .fichiers import compresser_photo
from .forms import (
    ActionCreationForm,
    ActionModificationForm,
    LieuForm,
    PhotoForm,
    PlanForm,
    PosteForm,
    ReglagesForm,
    RevueForm,
    UtilisateurCreationForm,
    UtilisateurModificationForm,
    ValeurFrequenceForm,
    ValeurGraviteForm,
    ValeurSatisfactionForm,
)
from .models import (
    Action,
    ChangementSatisfaction,
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


def animateur_seulement(vue):
    """M8 : l'équipe et les paramètres du club se gèrent entre
    animateurs — l'admin Django reste au secrétariat."""

    @wraps(vue)
    def interne(request, *args, **kwargs):
        if not request.user.is_animateur:
            raise PermissionDenied(
                "L'équipe et les paramètres se gèrent entre animateurs."
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


def dec6(valeur):
    """Flottant formaté en point décimal (jamais virgule locale), ou None.

    Les templates rendent les nombres à la française — « 48,42 » — et
    parseFloat côté navigateur s'arrête à la virgule : la carte s'ouvrait
    à lat 48, des dizaines de kilomètres trop au sud (découvert en
    exploitation). Les positions passées aux attributs data-lat/lng
    sont donc formatées ici en chaînes que le template rend telles
    quelles.
    """
    return None if valeur is None else f"{valeur:.6f}"


def centre_decimaux():
    """Centre de carte initial (réglages du club, à défaut le .env)
    en point décimal."""
    courants = Reglages.charge()
    return (
        dec6(courants.centre_latitude),
        dec6(courants.centre_longitude),
    )


def zoom_courant():
    """Zoom de carte initial (réglages du club, à défaut le .env)."""
    return Reglages.charge().zoom_carte


def plans_pour_cartes():
    """Plans de bâtiments sérialisés pour toutes les cartes : la grande
    (M3) et les mini-cartes de saisie (M6 sous le marqueur)."""
    return [plan.donnees_carte() for plan in PlanBatiment.objects.all()]


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
        "plans": plans_pour_cartes(),
    }
    context = {
        "section": "carte",
        "donnees_carte": donnees_carte,
        "centre": centre_decimaux(),
        "zoom": zoom_courant(),
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
            # Toutes les photos de chaque côté : plusieurs « avant » et
            # plusieurs « après » s'affichent empilées dans la comparaison.
            "photos_avant": photos_avant,
            "photos_apres": list(action.photos_apres.all()),
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
            "centre": centre_decimaux(),
            "zoom": zoom_courant(),
            "plans": plans_pour_cartes(),
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
            "poste_lat": dec6(poste.latitude),
            "poste_lng": dec6(poste.longitude),
            "centre": centre_decimaux(),
            "zoom": zoom_courant(),
            "plans": plans_pour_cartes(),
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
    # Retour au passage guidé : accepté uniquement s'il désigne
    # exactement l'écran du poste en cours d'examen — ajouter une
    # action pendant une revue n'interrompt pas la revue.
    retour = None
    retour_demande = request.GET.get("retour") or request.POST.get("retour")
    if revue and retour_demande:
        attendu = reverse("revue_passage", args=[revue.pk, poste.pk])
        if retour_demande == attendu:
            retour = attendu

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
        if retour:
            # Retour au passage guidé : le message atteste que
            # l'action est enregistrée — on revient au poste, la
            # fiche action ne s'ouvre pas (elle interromprait la
            # revue). Hors passage, pas de message : la fiche
            # s'ouvre, elle se suffit à elle-même.
            messages.success(
                request, f"Action « {action.intitule} » créée."
            )
            return redirect(retour)
        return redirect("action_detail", pk=action.pk)
    return render(
        request,
        "core/action_form.html",
        {
            "section": "actions",
            "form": form,
            "titre": "Nouvelle action",
            "poste": poste,
            "poste_lat": dec6(poste.latitude),
            "poste_lng": dec6(poste.longitude),
            "revue": revue,
            "retour": retour,
            "centre": centre_decimaux(),
            "zoom": zoom_courant(),
            "plans": plans_pour_cartes(),
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
            "action_lat": dec6(action.latitude),
            "action_lng": dec6(action.longitude),
            "poste_lat": dec6(action.poste.latitude),
            "poste_lng": dec6(action.poste.longitude),
            "centre": centre_decimaux(),
            "zoom": zoom_courant(),
            "plans": plans_pour_cartes(),
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
def action_statut(request, pk, statut):
    """Changement rapide de statut depuis la fiche (POST uniquement) :
    démarrer, clôturer, remettre à faire, rouvrir. L'abandon reste
    l'affaire du formulaire complet — il exige son motif. La clôture
    se date et la réouverture l'efface (même save() que l'édition),
    les revues en tirent leurs « actions clôturées depuis la
    précédente »."""
    action = get_object_or_404(
        Action.objects.select_related("poste"), pk=pk
    )
    if not action.peut_etre_modifiee_par(request.user):
        raise PermissionDenied(
            "Seul le responsable ou l'animateur change le statut "
            "d'une action."
        )
    cibles = {
        "en_cours": Action.Statut.EN_COURS,
        "faite": Action.Statut.FAITE,
        "rouvrir": Action.Statut.A_FAIRE,
    }
    transitions = {
        Action.Statut.A_FAIRE: {Action.Statut.EN_COURS, Action.Statut.FAITE},
        Action.Statut.EN_COURS: {Action.Statut.A_FAIRE, Action.Statut.FAITE},
        Action.Statut.FAITE: {Action.Statut.A_FAIRE},
    }
    cible = cibles.get(statut)
    if cible is None or cible not in transitions.get(action.statut, set()):
        raise Http404("Changement de statut inconnu.")
    if request.method == "POST":
        action.statut = cible
        action.save()
        if action.statut == Action.Statut.FAITE and not action.photos_apres.exists():
            # Règle 5 des écrans : clôturer sans photo « après » se
            # signale, sans jamais bloquer.
            messages.warning(
                request,
                "Action clôturée sans photo « après » : ajoute-la, "
                "elle témoigne du travail accompli.",
            )
        else:
            messages.success(
                request,
                f"Action {action.get_statut_display().lower()}.",
            )
    return redirect("action_detail", pk=action.pk)


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
def photo_supprimer(request, pk):
    """Supprime une photo et son fichier (POST uniquement) : quiconque
    est connecté peut retomber sur un import erroné. Le retour se
    fait sur la fiche d'où la photo vient."""
    photo = get_object_or_404(Photo, pk=pk)
    if photo.poste:
        cible = redirect("poste_detail", pk=photo.poste.pk)
    else:
        cible = redirect("action_detail", pk=photo.action.pk)
    if request.method == "POST":
        if photo.fichier:
            photo.fichier.delete(save=False)
        photo.delete()
        messages.success(request, "Photo supprimée, fichier retiré.")
    return cible


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
def revue_supprimer(request, pk):
    """Supprime une revue VIDE (POST uniquement) : les revues
    d'essai partent, celles qui portent une décision ou une action
    restent au journal (règle 1)."""
    revue = get_object_or_404(Revue, pk=pk)
    if request.method == "POST":
        try:
            revue.delete()
        except PermissionDenied:
            messages.error(
                request,
                "Cette revue porte des décisions ou des actions : "
                "elle reste au journal.",
            )
            return redirect("revue_detail", pk=revue.pk)
        messages.success(
            request,
            f"Revue du {revue.date:%d/%m/%Y} supprimée (aucune "
            "décision ni action n'y était consignée).",
        )
        return redirect("revues")
    return redirect("revue_detail", pk=revue.pk)


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
            "photos_avant": action.poste.photos_avant.all(),
            "photos_apres": action.photos_apres.all(),
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
        # Une revue vide (aucune décision, aucune action) peut être
        # une revue d'essai : la fiche propose alors la suppression.
        "revue_vide": not revue.changements.exists()
        and not revue.actions.exists(),
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
    retour_attendu = reverse("revue_detail", args=[revue.pk])
    ancre = f"{retour_attendu}#poste-{poste.pk}"
    # Un retour au passage guidé est accepté uniquement s'il désigne
    # exactement l'écran courant : pas de redirection vers n'importe quoi.
    passage = reverse("revue_passage", args=[revue.pk, poste.pk])
    if request.POST.get("retour") == passage:
        ancre = passage
    return redirect(ancre)


@login_required
def revue_selection(request, pk):
    """Nouveau process (M9) — étape 1 du passage guidé : on coche
    d'un coup les postes à passer en revue. Défaut : tout ce qui
    n'est pas archivé ; si la revue a déjà ses postes, ce sont eux
    qui sont cochés. Les postes archivés déjà examinés restent
    dans la revue (règle 1 : rien ne disparaît)."""
    revue = get_object_or_404(Revue, pk=pk)
    aujourdhui = timezone.localdate()
    postes = (
        Poste.objects.filter(archive=False)
        .select_related("lieu", "gravite", "satisfaction")
        .annotate(
            ouvertes=Count(
                "actions",
                filter=Q(
                    actions__statut__in=[
                        Action.Statut.A_FAIRE,
                        Action.Statut.EN_COURS,
                    ]
                ),
            ),
            retards=Count(
                "actions",
                filter=Q(
                    actions__statut__in=[
                        Action.Statut.A_FAIRE,
                        Action.Statut.EN_COURS,
                    ],
                    actions__echeance__lt=aujourdhui,
                ),
            ),
        )
        .order_by("nom")
    )
    if request.method == "POST":
        coches = Poste.objects.filter(
            pk__in=request.POST.getlist("postes"), archive=False
        )
        # Les archivés déjà examinés ne sont pas décochables : la
        # sélection ne les retire jamais.
        revue.postes.set(
            list(coches) + list(revue.postes.filter(archive=True))
        )
        return redirect("revue_passage_debut", pk=revue.pk)
    examines = list(revue.postes.values_list("pk", flat=True))
    if not examines:
        examines = list(postes.values_list("pk", flat=True))
    return render(
        request,
        "core/revue_selection.html",
        {
            "section": "revues",
            "revue": revue,
            "postes": postes,
            "coches": examines,
        },
    )


@login_required
def revue_passage_debut(request, pk):
    """Étape 2 : direction le premier poste à examiner (ordre
    alphabétique, comme la sélection), ou retour au journal si
    la revue n'examine aucun poste."""
    revue = get_object_or_404(Revue, pk=pk)
    premier = revue.postes.filter(archive=False).order_by("nom").first()
    if not premier:
        messages.info(
            request,
            "Aucun poste à examiner : coche d'abord les postes "
            "à passer en revue.",
        )
        return redirect("revue_detail", pk=revue.pk)
    return redirect("revue_passage", pk=revue.pk, poste_pk=premier.pk)


@login_required
def revue_passage(request, pk, poste_pk):
    """Étape 3 — le passage proprement dit : un poste à la fois,
    tout le poste (gravité, historique, actions, photos), la
    décision collégiale à portée de main, puis le suivant."""
    revue = get_object_or_404(
        Revue.objects.prefetch_related("postes"), pk=pk
    )
    postes = list(revue.postes.filter(archive=False).order_by("nom"))
    poste = next((p for p in postes if p.pk == poste_pk), None)
    if poste is None:
        raise Http404("Poste non examiné par cette revue.")
    rang = postes.index(poste)
    precedent = postes[rang - 1] if rang > 0 else None
    suivant = postes[rang + 1] if rang + 1 < len(postes) else None
    paires = [
        {
            "action": action,
            "photos_avant": action.poste.photos_avant.all(),
            "photos_apres": action.photos_apres.all(),
        }
        for action in Action.objects.filter(
            poste=poste, statut=Action.Statut.FAITE, date_cloture__isnull=False
        ).order_by("-date_cloture")
    ]
    return render(
        request,
        "core/revue_passage.html",
        {
            "section": "revues",
            "revue": revue,
            "poste": poste,
            "rang": rang + 1,
            "total": len(postes),
            "precedent": precedent,
            "suivant": suivant,
            "satisfactions": ValeurSatisfaction.objects.all(),
            "photos_avant": poste.photos_avant.select_related("auteur"),
            "changements": poste.changements_satisfaction.select_related(
                "ancienne", "nouvelle", "revue"
            ),
            "paires": paires,
        },
    )


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
        courants = Reglages.charge()
        return (courants.centre_latitude, courants.centre_longitude)
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
    courants = Reglages.charge()
    zoom = courants.zoom_carte if not plan.forme else 18
    donnees_dessin = {
        "lat": courants.centre_latitude,
        "lng": courants.centre_longitude,
        "zoom": zoom,
        "couleur": plan.couleur,
        "forme": plan.forme,
    }
    if plan.forme:
        latitude, longitude = centre_de_coins(plan.forme["coordinates"][0])
        donnees_dessin["lat"] = latitude
        donnees_dessin["lng"] = longitude
    # Bâtiments déjà en place : repères sous le tracé, pour situer le
    # nouveau plan parmi les autres sans jouer aux devinettes. Le
    # plan en cours s'affiche à part (relecture), les inachevés
    # n'ont rien à montrer.
    autres_plans = [
        autre.donnees_carte()
        for autre in PlanBatiment.objects.exclude(pk=plan.pk)
        if autre.est_complet()
    ]
    return render(
        request,
        "core/plan_dessin.html",
        {
            "section": "plans",
            "plan": plan,
            "donnees_dessin": donnees_dessin,
            "plans": autres_plans,
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
    courants_calibration = Reglages.charge()
    lat, lng = courants_calibration.centre_latitude, courants_calibration.centre_longitude
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
        "zoom": courants_calibration.zoom_carte,
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


# Équipe et paramètres (M8) ----------------------------------------------------
# Pages intégrées à l'app, en français, pour les animateurs : plus
# besoin de l'admin Django pour créer un compte ou régler une liste.


LISTES_VALEURS = {
    "lieux": {
        "modele": Lieu,
        "form": LieuForm,
        "titre": "Lieux du club",
        "singulier": "lieu",
        "avec_couleur": False,
    },
    "gravites": {
        "modele": ValeurGravite,
        "form": ValeurGraviteForm,
        "titre": "Gravités potentielles",
        "singulier": "gravité",
        "avec_couleur": True,
    },
    "frequences": {
        "modele": ValeurFrequence,
        "form": ValeurFrequenceForm,
        "titre": "Fréquences d'exposition",
        "singulier": "fréquence",
        "avec_couleur": True,
    },
    "satisfactions": {
        "modele": ValeurSatisfaction,
        "form": ValeurSatisfactionForm,
        "titre": "Statuts de satisfaction",
        "singulier": "statut",
        "avec_couleur": True,
    },
}


def _liste_ou_404(liste):
    descr = LISTES_VALEURS.get(liste)
    if descr is None:
        raise Http404("Liste de valeurs inconnue.")
    return descr


@login_required
@animateur_seulement
def equipe(request):
    """Comptes du club : la liste, avec rôles et état d'activation."""
    liste = Utilisateur.objects.order_by("username")
    return render(
        request,
        "core/equipe_liste.html",
        {"section": "equipe", "utilisateurs": liste},
    )


@login_required
@animateur_seulement
def equipe_creer(request):
    """Nouveau compte : identifiant, nom, mot de passe, rôle."""
    if request.method == "POST":
        form = UtilisateurCreationForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            messages.success(
                request,
                f"Compte « {utilisateur.username} » créé.",
            )
            return redirect("equipe")
    else:
        form = UtilisateurCreationForm()
    return render(
        request,
        "core/equipe_form.html",
        {"section": "equipe", "titre": "Nouveau compte", "form": form},
    )


@login_required
@animateur_seulement
def equipe_modifier(request, pk):
    """Édition d'un compte ; garde-fous : un animateur non staff ne
    touche pas un compte du secrétariat, et personne ne se retire
    lui-même son rôle ni ne désactive son propre compte."""
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    if utilisateur.is_staff and not request.user.is_staff:
        raise PermissionDenied(
            "Les comptes du secrétariat se gèrent dans l'admin Django."
        )
    if request.method == "POST":
        form = UtilisateurModificationForm(request.POST, instance=utilisateur)
        if form.is_valid():
            donnees = form.cleaned_data
            if utilisateur.pk == request.user.pk and (
                not donnees["is_animateur"] or not donnees["is_active"]
            ):
                form.add_error(
                    None,
                    "Un animateur ne se retire pas lui-même son rôle "
                    "et ne désactive pas son propre compte.",
                )
            else:
                mot = donnees.get("nouveau_mot_de_passe")
                form.save()
                messages.success(
                    request,
                    f"Compte « {utilisateur.username} » mis à jour."
                    + (" Mot de passe remplacé." if mot else ""),
                )
                return redirect("equipe")
    else:
        form = UtilisateurModificationForm(instance=utilisateur)
    return render(
        request,
        "core/equipe_form.html",
        {
            "section": "equipe",
            "titre": f"Modifier « {utilisateur.username} »",
            "form": form,
            "utilisateur": utilisateur,
        },
    )


def _parametres_contexte(form_reglages=None):
    """Contexte commun de la page Paramètres : les quatre listes de
    valeurs (avec leur formulaire d'ajout) et les réglages de carte.
    Chaque liste porte son prochain ordre (les nouvelles valeurs se
    rangent à la fin) et le nom du champ texte (les lieux disent
    « nom », les cotations « libelle »)."""
    classe_form = form_reglages.__class__ if form_reglages else ReglagesForm
    listes = []
    for slug, descr in LISTES_VALEURS.items():
        modele = descr["modele"]
        prochain = 1 + (
            modele.objects.aggregate(Max("ordre"))["ordre__max"] or 0
        )
        listes.append(
            {
                "slug": slug,
                "titre": descr["titre"],
                "avec_couleur": descr["avec_couleur"],
                "valeurs": modele.objects.all(),
                "form": descr["form"](),
                "champ_texte": "nom"
                if slug == "lieux"
                else "libelle",
                "prochain_ordre": prochain,
            }
        )
    return {
        "section": "parametres",
        "listes": listes,
        "form_reglages": form_reglages or classe_form(
            instance=Reglages.charge()
        ),
        "plans": plans_pour_cartes(),
        "centre": centre_decimaux(),
        "zoom": zoom_courant(),
    }


@login_required
@animateur_seulement
def parametres(request):
    """Les listes qui structurent les postes, et la carte du club."""
    return render(request, "core/parametres.html", _parametres_contexte())


@login_required
@animateur_seulement
def parametres_carte(request):
    """Centre et zoom initiaux des cartes (une seule ligne de réglages)."""
    if request.method == "POST":
        form = ReglagesForm(request.POST, instance=Reglages.charge())
        if form.is_valid():
            form.save()
            messages.success(
                request, "Réglages de la carte enregistrés."
            )
            return redirect("parametres")
        # Formulaire en erreur : on reparde la page, champs remplis.
        messages.error(
            request, "Réglages refusés : corrige les valeurs."
        )
        return render(
            request, "core/parametres.html", _parametres_contexte(form)
        )
    return redirect("parametres")


@login_required
@animateur_seulement
def parametres_valeur_ajouter(request, liste):
    """Ajout dans une liste de valeurs, depuis la page Paramètres."""
    descr = _liste_ou_404(liste)
    if request.method == "POST":
        form = descr["form"](request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"{descr['singulier'].capitalize()} ajouté."
            )
        else:
            messages.error(
                request,
                "Ajout refusé : vérifie le nom et l'ordre d'affichage.",
            )
    return redirect("parametres")


@login_required
@animateur_seulement
def parametres_ordre(request, liste):
    """Réordonnancement d'une liste au glisser-déposer (POST
    uniquement) : la liste des identifiants dans l'ordre visé
    réécrit les rangs 1..n. Identifiants inconnus ou en double :
    refus franc, rien ne bouge (règle : rien ne disparaît)."""
    descr = _liste_ou_404(liste)
    if request.method == "POST":
        brutes = request.POST.get("ordre", "").split(",")
        try:
            pks = [int(morceau) for morceau in brutes if morceau.strip()]
        except ValueError:
            pks = None
        valeurs = (
            list(descr["modele"].objects.filter(pk__in=pks))
            if pks
            else []
        )
        if not pks or len(valeurs) != len(pks):
            messages.error(
                request,
                "Réordonnancement refusé : valeurs inconnues ou "
                "répétées.",
            )
            return redirect("parametres")
        par_pk = {valeur.pk: valeur for valeur in valeurs}
        for rang, pk in enumerate(pks, start=1):
            valeur = par_pk[pk]
            if valeur.ordre != rang:
                valeur.ordre = rang
                valeur.save(update_fields=["ordre"])
        messages.success(request, "Nouvel ordre enregistré.")
    return redirect("parametres")


@login_required
@animateur_seulement
def parametres_valeur_modifier(request, liste, pk):
    """Modification d'une valeur d'une liste."""
    descr = _liste_ou_404(liste)
    valeur = get_object_or_404(descr["modele"], pk=pk)
    if request.method == "POST":
        form = descr["form"](request.POST, instance=valeur)
        if form.is_valid():
            form.save()
            messages.success(request, "Valeur mise à jour.")
            return redirect("parametres")
    else:
        form = descr["form"](instance=valeur)
    return render(
        request,
        "core/parametres_form.html",
        {
            "section": "parametres",
            "titre": f"Modifier : {valeur}",
            "form": form,
        },
    )


@login_required
@animateur_seulement
def parametres_valeur_supprimer(request, liste, pk):
    """Suppression d'une valeur inutilisée — une valeur citée par des
    postes ou le journal ne disparaît jamais (règle 1, PROTECT)."""
    descr = _liste_ou_404(liste)
    valeur = get_object_or_404(descr["modele"], pk=pk)
    if request.method == "POST":
        from django.db.models import ProtectedError

        try:
            valeur.delete()
        except ProtectedError:
            messages.error(
                request,
                f"« {valeur} » est cité par des postes ou des revues : "
                "il ne peut pas disparaître.",
            )
        else:
            messages.success(request, "Valeur retirée de la liste.")
    return redirect("parametres")
