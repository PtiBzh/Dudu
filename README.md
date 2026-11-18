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

## État : M2 (actions)

- [x] M0 : socle — projet Django, comptes identifiés + rôle animateur, login, admin, interface de base, CI
- [x] M1 : postes — création libre, fiche, liste filtrable (lieu, satisfaction, gravité, recherche), cotation santé/sécurité, édition tracée, archivage (aucune suppression)
- [x] Actions : responsable et échéance obligatoires (règle 2), plusieurs actions possibles par poste
- [x] Création hors revue réservée à l'animateur (règle 5), inscrite d'office à la prochaine revue (les revues arrivent en M4)
- [x] Statuts à faire / en cours / faite / abandonnée, abandon avec motif obligatoire
- [x] Liste des actions : filtres statut, responsable, retards en évidence ; compteurs au tableau de bord
- [ ] M3 : carte · M4 : revues · M5 : photos
- [ ] M6 : plans de bâtiments · M7 : conteneur, sauvegarde, déploiement
