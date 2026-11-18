# Dudu

[![CI](https://github.com/PtiBzh/Dudu/actions/workflows/ci.yml/badge.svg)](https://github.com/PtiBzh/Dudu/actions/workflows/ci.yml)

Suivi d'amélioration des conditions de travail — Centre Nautique.

Dudu recense les **postes de travail** de l'équipe, suit leur **niveau de
satisfaction** et leur cotation **santé/sécurité**, et pilote les **actions**
décidées collégialement en revue. Chaque poste est positionné sur une carte
du club (orthophoto IGN), avec photos avant/après.

> Dudu n'est pas le DUERP du club : c'est un outil de terrain qui l'alimente,
> sans le remplacer.

## Documentation

- **Spec Dudu.md** — spécification fonctionnelle (référence métier)
- **Spec technique.md** — architecture, modèle de données, jalons M0 à M7

## Stack

Django + SQLite + HTMX, MapLibre GL JS + Terra Draw pour la carte.
Un seul conteneur en production, réseau local + WireGuard, aucune
exposition publique. Voir la spec technique.

## Démarrage (développement)

```bash
python3 -m venv .venv
source .venv/bin/activate        # bash, zsh…
# sous fish : source .venv/bin/activate.fish
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

L'application : http://127.0.0.1:8000 · Admin : http://127.0.0.1:8000/admin/

## Tests

```bash
python manage.py test
```

Chaque push déclenche la CI (GitHub Actions) : générations des migrations
manquantes, migration, tests. Les migrations manquantes sont committées
automatiquement par la CI (validées par les tests), on ne les écrit jamais
à la main. Elle télécharge et committe aussi les bibliothèques vendored
(MapLibre GL JS, empreintes vérifiées). En cas d'échec, elle commite un
« Diagnostic CI.txt » avec le détail complet de l'erreur.

## État : M6 (plans)

- [x] M0 : socle — projet Django, comptes identifiés + rôle animateur, login, admin, interface de base, CI
- [x] M1 : postes — création libre, fiche, liste filtrable (lieu, satisfaction, gravité, recherche), cotation santé/sécurité, édition tracée, archivage (aucune suppression)
- [x] M2 : actions — responsable et échéance obligatoires (règle 2), statuts dont abandon avec motif, création hors revue réservée à l'animateur (règle 5), retards en évidence
- [x] M3 : carte — fond orthophoto IGN (MapLibre GL JS), mêmes filtres que la liste, positionnement du poste d'un clic sur la mini-carte (obligatoire), marqueurs couleur gravité + halo satisfaction, actions ouvertes en pastilles, lien fiche ↔ carte
- [x] M4 : revues — journal historique : date, participants, postes examinés, décisions de satisfaction consignées (règle 3, journal immuable), actions créées en revue par toute l'équipe, compte rendu, historique de satisfaction sur le poste
- [x] M5 : photos — « avant » au poste (toute l'équipe), « après » à l'action (responsable ou animateur), compression ~1600 px JPEG qualité 85 à l'upload (Pillow, EXIF respecté), stockage data/photos/AAAA/, avertissement non bloquant si clôture sans photo (règle 5), galeries avant/après sur le poste et en revue
- [x] M6 : plans de bâtiments — formes dessinées à la souris (Terra Draw, éditeur dédié) ou images PNG/JPG calées par 4 coins WGS84 (éditeur maison : poignées, déplacement, échelle, opacité), étages côte à côte jamais empilés, affichage sous les marqueurs sur la carte, gestion réservée au staff
- [ ] M7 : conteneur, sauvegarde, déploiement
