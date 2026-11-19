"""Jeu de valeurs par défaut : lieux, gravités, fréquences, satisfactions.

Remplit chaque liste de référence uniquement si elle est VIDE : ce qui
existe déjà (données du club, tests) n'est ni écrasé ni dupliqué, et
tout reste modifiable dans l'admin — la spec les y range d'office.
"""
from django.db import migrations

LIEUX = [
    ("Accueil", 1),
    ("Hangar", 2),
    ("Parc à bateaux", 3),
    ("Slip", 4),
]

GRAVITES = [
    ("Faible", 1, "#fdd835"),
    ("Modérée", 2, "#fb8c00"),
    ("Élevée", 3, "#c62828"),
]

FREQUENCES = [
    ("Occasionnelle", 1, "#6b7684"),
    ("Hebdomadaire", 2, "#6b7684"),
    ("Quotidienne", 3, "#6b7684"),
]

SATISFACTIONS = [
    ("Satisfaisant", 1, "#2e7d32"),
    ("À améliorer", 2, "#f9a825"),
    ("Critique", 3, "#c62828"),
]


def remplir_si_vide(apps, schema_editor):
    Lieu = apps.get_model("core", "Lieu")
    Gravite = apps.get_model("core", "ValeurGravite")
    Frequence = apps.get_model("core", "ValeurFrequence")
    Satisfaction = apps.get_model("core", "ValeurSatisfaction")

    if not Lieu.objects.exists():
        Lieu.objects.bulk_create(
            [Lieu(nom=nom, ordre=ordre) for nom, ordre in LIEUX]
        )
    if not Gravite.objects.exists():
        Gravite.objects.bulk_create(
            [Gravite(libelle=l, ordre=o, couleur=c) for l, o, c in GRAVITES]
        )
    if not Frequence.objects.exists():
        Frequence.objects.bulk_create(
            [Frequence(libelle=l, ordre=o, couleur=c) for l, o, c in FREQUENCES]
        )
    if not Satisfaction.objects.exists():
        Satisfaction.objects.bulk_create(
            [
                Satisfaction(libelle=l, ordre=o, couleur=c)
                for l, o, c in SATISFACTIONS
            ]
        )


class Migration(migrations.Migration):

    dependencies = [("core", "0009_alter_planbatiment_couleur_and_more")]

    operations = [
        migrations.RunPython(remplir_si_vide, migrations.RunPython.noop),
    ]
