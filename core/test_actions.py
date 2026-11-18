"""Tests M2 : actions — règles 1, 2 et 5 de la spec fonctionnelle.

1. Une action sans responsable ni échéance ne peut pas être créée.
2. Hors revue (les revues arrivent en M4), la création d'action est
   réservée à l'animateur ; l'action est inscrite d'office à la
   prochaine revue.
3. Rien ne disparaît : une action ne se supprime pas ; abandonnée,
   elle exige un motif et reste visible.
"""
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Action, Poste, Utilisateur


class ActionFixture(TestCase):
    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.lea = Utilisateur.objects.create_user(
            "lea", password="mot de passe-123", is_animateur=True
        )
        self.client.login(username="lea", password="mot de passe-123")
        self.poste = Poste.objects.create(
            nom="Manutention remorque planches",
            description="La remorque est trop haute, on se cogne la tête.",
            auteur=self.alice,
            latitude=48.1,
            longitude=-4.5,
        )
        self.dans_une_semaine = timezone.localdate() + timedelta(days=7)
        self.hier = timezone.localdate() - timedelta(days=1)

    def donnees_action(self, **modifs):
        donnees = {
            "intitule": "Sortir les planches sans se cogner la tête",
            "description": "Ranger un marchepied près de la remorque.",
            "responsable": self.alice.id,
            "echeance": self.dans_une_semaine.isoformat(),
            "latitude": "",
            "longitude": "",
        }
        donnees.update(modifs)
        return donnees

    def creer_action(self, **modifs):
        self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(**modifs),
        )
        return Action.objects.first()


class CreationActionTests(ActionFixture):
    def test_l_animateur_cree_une_action(self):
        reponse = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(),
        )
        action = Action.objects.first()
        self.assertRedirects(
            reponse, reverse("action_detail", args=[action.pk])
        )
        self.assertEqual(action.poste, self.poste)
        self.assertEqual(action.responsable, self.alice)
        self.assertEqual(action.statut, Action.Statut.A_FAIRE)
        self.assertEqual(action.echeance, self.dans_une_semaine)

    def test_marquee_a_inscrire_a_la_prochaine_revue(self):
        """Règle 5 : créée hors revue, l'action est inscrite d'office
        à la prochaine revue."""
        action = self.creer_action()
        reponse = self.client.get(
            reverse("action_detail", args=[action.pk])
        )
        self.assertContains(reponse, "prochaine revue")

    def test_creation_reservee_a_l_animateur(self):
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(),
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(Action.objects.count(), 0)

    def test_creation_anonyme_refusee(self):
        self.client.logout()
        reponse = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(),
        )
        self.assertEqual(reponse.status_code, 302)  # vers la connexion

    def test_action_sans_responsable_refusee(self):
        """Règle 2 : pas de responsable, pas d'action."""
        reponse = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(responsable=""),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(Action.objects.count(), 0)
        self.assertTrue(
            reponse.context["form"].errors.get("responsable"),
            "Le responsable doit être signalé comme obligatoire.",
        )

    def test_action_sans_echeance_refusee(self):
        """Règle 2 : pas d'échéance, pas d'action."""
        reponse = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(echeance=""),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(Action.objects.count(), 0)
        self.assertTrue(reponse.context["form"].errors.get("echeance"))

    def test_position_heritee_du_poste(self):
        action = self.creer_action(latitude="", longitude="")
        self.assertEqual(action.latitude, self.poste.latitude)
        self.assertEqual(action.longitude, self.poste.longitude)

    def test_position_modifiable_a_la_creation(self):
        action = self.creer_action(latitude="48.2", longitude="-4.6")
        self.assertEqual(action.latitude, 48.2)
        self.assertEqual(action.longitude, -4.6)


class EditionActionTests(ActionFixture):
    def test_le_responsable_peut_passer_faire(self):
        action = self.creer_action()
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.post(
            reverse("action_modifier", args=[action.pk]),
            self.donnees_action(statut=Action.Statut.FAITE),
        )
        self.assertRedirects(
            reponse, reverse("action_detail", args=[action.pk])
        )
        action.refresh_from_db()
        self.assertEqual(action.statut, Action.Statut.FAITE)

    def test_l_echeance_peut_etre_decalee(self):
        action = self.creer_action()
        plus_tard = timezone.localdate() + timedelta(days=30)
        self.client.post(
            reverse("action_modifier", args=[action.pk]),
            self.donnees_action(echeance=plus_tard.isoformat()),
        )
        action.refresh_from_db()
        self.assertEqual(action.echeance, plus_tard)

    def test_abandon_exige_un_motif(self):
        """Règle 1 : une action abandonnée reste visible avec son motif."""
        action = self.creer_action()
        reponse = self.client.post(
            reverse("action_modifier", args=[action.pk]),
            self.donnees_action(
                statut=Action.Statut.ABANDONNEE, motif_abandon=""
            ),
        )
        self.assertEqual(reponse.status_code, 200)
        action.refresh_from_db()
        self.assertNotEqual(action.statut, Action.Statut.ABANDONNEE)
        self.assertTrue(
            reponse.context["form"].errors.get("motif_abandon")
        )

    def test_abandon_avec_motif(self):
        action = self.creer_action()
        self.client.post(
            reverse("action_modifier", args=[action.pk]),
            self.donnees_action(
                statut=Action.Statut.ABANDONNEE,
                motif_abandon="On a acheté une remorque basse.",
            ),
        )
        action.refresh_from_db()
        self.assertEqual(action.statut, Action.Statut.ABANDONNEE)
        self.assertEqual(
            action.motif_abandon, "On a acheté une remorque basse."
        )

    def test_autrui_ne_peut_pas_modifier(self):
        action = self.creer_action()
        Utilisateur.objects.create_user("bob", password="mot de passe-123")
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.client.post(
            reverse("action_modifier", args=[action.pk]),
            self.donnees_action(statut=Action.Statut.FAITE),
        )
        self.assertEqual(reponse.status_code, 403)

    def test_pas_de_suppression_possible(self):
        """Règle 1 : rien ne disparaît."""
        action = self.creer_action()
        with self.assertRaises(PermissionDenied):
            action.delete()


class ListeActionTests(ActionFixture):
    def test_les_actions_ouvertes_sont_visibles_par_defaut(self):
        self.creer_action()
        self.creer_action(intitule="Ranger le matériel d'hivernage")
        reponse = self.client.get(reverse("actions"))
        self.assertContains(reponse, "Sortir les planches sans se cogner la tête")

    def test_les_faites_disparaissent_de_la_liste_ouverte(self):
        action = self.creer_action()
        action.statut = Action.Statut.FAITE
        action.save()
        reponse = self.client.get(reverse("actions"))
        self.assertNotContains(
            reponse, "Sortir les planches sans se cogner la tête"
        )
        reponse = self.client.get(reverse("actions"), {"statut": "toutes"})
        self.assertContains(
            reponse, "Sortir les planches sans se cogner la tête"
        )

    def test_retards_en_evidence(self):
        self.creer_action()
        self.creer_action(
            intitule="Réparer l'anse de remorquage",
            echeance=self.hier.isoformat(),
        )
        reponse = self.client.get(reverse("actions"), {"retard": 1})
        self.assertContains(reponse, "Réparer l'anse de remorquage")
        self.assertContains(reponse, "en retard")
        self.assertNotContains(
            reponse, "Sortir les planches sans se cogner la tête"
        )

    def test_une_faite_n_est_jamais_en_retard(self):
        action = self.creer_action(echeance=self.hier.isoformat())
        action.statut = Action.Statut.FAITE
        action.save()
        self.assertFalse(action.en_retard)

    def test_filtre_par_responsable(self):
        self.creer_action()
        reponse = self.client.get(
            reverse("actions"), {"responsable": self.alice.id}
        )
        self.assertContains(reponse, "Sortir les planches sans se cogner la tête")
        reponse = self.client.get(
            reverse("actions"), {"responsable": self.lea.id}
        )
        self.assertNotContains(
            reponse, "Sortir les planches sans se cogner la tête"
        )

    def test_le_poste_affiche_ses_actions(self):
        self.creer_action()
        reponse = self.client.get(
            reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertContains(reponse, "Sortir les planches sans se cogner la tête")

    def test_le_bouton_nouvelle_action_reserve_a_l_animateur(self):
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.get(
            reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertNotContains(
            reponse, reverse("action_creer", args=[self.poste.pk])
        )


class CompteurAccueilTests(ActionFixture):
    def test_le_tableau_de_bord_compte_les_retards(self):
        self.creer_action()
        self.creer_action(
            intitule="Réparer l'anse de remorquage",
            echeance=self.hier.isoformat(),
        )
        reponse = self.client.get(reverse("home"))
        self.assertContains(reponse, "actions ouvertes")
        self.assertContains(reponse, "actions en retard")
