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

Chaque push déclenche la CI (GitHub Actions) : génération des migrations
manquantes, migration, tests. Les migrations manquantes sont committées
automatiquement par la CI (validées par les tests), on ne les écrit jamais
à la main. En cas d'échec, la CI commite un « Diagnostic CI.txt » avec le
détail complet de l'erreur.

## État : M1 (postes)

- [x] M0 : socle — projet Django, comptes identifiés + rôle animateur, login, admin, interface de base, CI
- [x] Postes de travail : création libre, fiche, liste filtrable (lieu, satisfaction, gravité, recherche)
- [x] Cotation santé/sécurité (gravité, fréquence, origine du signalement)
- [x] Édition réservée à l'auteur ou à un animateur, chaque changement tracé
- [x] Archivage au lieu de la suppression (aucune donnée ne disparaît)
- [ ] M2 : actions · M3 : carte · M4 : revues · M5 : photos
- [ ] M6 : plans de bâtiments · M7 : conteneur, sauvegarde, déploiement
