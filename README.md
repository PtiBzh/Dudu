# Dudu

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
source .venv/bin/activate
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

Chaque push déclenche la CI (GitHub Actions) : cohérence des migrations,
migrations, tests. Un badge d'état sera ajouté une fois le premier run
exécuté.

## État : M0 (socle)

- [x] Projet Django, application unique `core`
- [x] Comptes identifiés (modèle Utilisateur) + rôle animateur
- [x] Connexion / déconnexion / admin
- [x] Squelette d'interface (base, accueil, messages)
- [x] CI GitHub Actions
- [ ] M1 : postes · M2 : actions · M3 : carte · M4 : revues · M5 : photos
- [ ] M6 : plans de bâtiments · M7 : conteneur, sauvegarde, déploiement
