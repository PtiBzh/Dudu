# Dudu — Suivi d'amélioration des conditions de travail

Application pour le Centre Nautique : recenser les postes de travail,
suivre leur niveau de satisfaction et leur risque, et piloter les actions
d'amélioration décidées collégialement.

> **Positionnement** : Dudu n'est pas le DUERP du club. C'est un outil de
> terrain qui **alimente** le document unique d'évaluation des risques
> professionnels, tenu par ailleurs, sans le remplacer. Les risques sérieux
> identifiés ici sont reportés dans le DUERP officiel.

## Objectif

Faire remonter et ne rien perdre des irritants et des risques du
quotidien (locaux, matériel, organisation), donner à l'équipe une vue
partagée de l'état de chaque poste, et transformer les décisions en
actions réellement assignées et suivies jusqu'à leur clôture.

## Utilisateurs et rôles

- **Équipe** : toute l'équipe du centre nautique, identifiée (pas
  d'anonymat). Chacun crée des postes, commente, consulte tout.
- **Animateur de l'app** : rôle assignable. Il trie et prépare les postes
  pour la revue en réunion (fusion des doublons, mise en forme tracée
  « modifiée par X le Y »), veille à ce que rien ne reste en rade. Rôle
  de secrétariat, pas de décisionnaire.
- **Responsable d'action** : désigné lors de la validation collégiale.
  Un par action.

## Objets

### Poste
Un aspect récurrent du travail au club.
Exemples : Manutention remorque planches, Accueil des gens,
Vestiaire mono.

- Nom, description
- Auteur, date de création
- Lieu (Hangar, Parc, Accueil… liste modifiable dans l'admin),
  sert de filtre rapide
- **Position sur la carte** : unique, obligatoire à la création
- **Statut de satisfaction** : liste de valeurs modifiable dans l'admin
  (valeurs par défaut : Satisfaisant / À améliorer / Critique),
  mis à jour uniquement en revue collégiale ; chaque changement
  demandé en revue est journalisé
- **Bloc Santé / Sécurité** (distinct de la satisfaction) :
  - Gravité potentielle et fréquence d'exposition : deux listes
    déroulantes (modifiables dans l'admin)
  - Origine du signalement : constat / presqu'accident / accident
  - Modifiable à tout moment (traduit un état constaté, pas une
    décision collective)
- **Photos typées** : « avant » pour documenter la situation constatée
- Commentaires (qui, quand)

### Action
- Créée depuis un poste, lors d'une revue collégiale — ou **hors revue
  en urgence** par l'animateur si le risque est grave (elle est alors
  inscrite d'office à la prochaine revue)
- Un poste peut porter **plusieurs actions** suivies en parallèle
- Intitulé, description de travail
- Responsable **obligatoire** à la création
- Échéance **obligatoire** à la création (décalable ensuite)
- **Statut de réalisation** : à faire / en cours / faite / abandonnée
  (avec motif)
- Position héritée du poste, modifiable
- **Photo « après »** demandée au passage en état « faite »
- Commentaires (qui, quand)
- Vue **avant / après** côte à côte, affichée sur le poste et en revue :
  témoin visuel du chemin parcouru

### Revue de réunion
Journal historique des choix de l'équipe :
- Date, participants, postes examinés
- Statuts de satisfaction décidés (avec journal des changements)
- Actions créées (y compris les urgentes créées hors revue depuis
  la précédente), décisions prises

## Règles de gestion

1. Rien ne disparaît : un poste n'est jamais supprimé (au mieux
   archivé), une action abandonnée reste visible avec son motif.
2. Une action sans responsable ni échéance ne peut pas être créée.
3. Le statut de satisfaction n'est modifié qu'en revue collégiale ;
   la cotation santé/sécurité est modifiable à tout moment.
4. La création d'un poste est libre pour toute l'équipe ; l'édition
   par l'animateur est tracée (« modifiée par X le Y »).
5. Un risque grave ne patiente pas : action urgente possible hors
   revue, par l'animateur.
6. Toute l'équipe voit tout.

## Carte du club

La liste et la carte sont les deux vues de la même donnée.

- **Fond** : orthophoto IGN (couche de tuiles, attribution IGN)
- **Plans de bâtiments** : dessinés dans l'app avec des formes simples
  (polygones) ; chaque étage est un plan placé côte à côte aux autres,
  pas empilé
- Chaque poste porte un point ; cliquer un marqueur ouvre le poste,
  et inversement depuis la liste
- Actions et postes apparaissent sur la carte ; couleurs des marqueurs
  selon la cotation santé/sécurité

## Hors périmètre v1

- Relances automatiques par email (candidat v2)
- Anonymat des propositions
- Multi-organisation
- Application mobile dédiée (site consultable sur mobile suffit)

## Choix techniques

- **Stack** : Django + SQLite + HTMX, MapLibre GL JS + Terra Draw pour la
  carte et le dessin des plans, bibliothèques chargées en fichiers
  statiques (pas de build front) ; un pont JavaScript minimal relie
  l'instance de carte et le flux HTMX
- **Photos** : redimensionnées côté serveur (~1600 px, JPEG qualité
  correcte) pour contenir le poids du stockage et des sauvegardes
- **Authentification** : comptes Django, identifiés, pas de SSO
- **Déploiement** : conteneur unique, serveur local du club
- **Accès** : réseau local + WireGuard, pas d'exposition publique
- **Usage** : desktop au bureau prioritaire, rendu mobile correct en
  consultation
- **Sauvegarde** : copie quotidienne automatique de la base et des
  photos vers un second emplacement (script + cron dans le conteneur)
