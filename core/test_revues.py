"""Tests M4 : revues — règle 3 (la satisfaction ne se décide qu'en
revue collégiale, chaque changement journalisé), règle 5 (action
urgente hors revue réservée à l'animateur, action collégiale en
revue), règle 1 (le journal historique ne disparaît jamais)."""
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Action,
    ChangementSatisfaction,
    Poste,
    Revue,
    Utilisateur,
    ValeurSatisfaction,
)


class RevueFixture(TestCase):
    """Alice (équipe), Lea (animatrice), un poste, une revue tenue hier."""

    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.lea = Utilisateur.objects.create_user(
            "lea", password="mot de passe-123", is_animateur=True
        )
        self.client.login(username="alice", password="mot de passe-123")
        self.satisfaisant = ValeurSatisfaction.objects.create(
            libelle="Satisfaisant", ordre=1, couleur="#2e7d32"
        )
        self.a_ameliorer = ValeurSatisfaction.objects.create(
            libelle="À améliorer", ordre=2, couleur="#ef6c00"
        )
        self.critique = ValeurSatisfaction.objects.create(
            libelle="Critique", ordre=3, couleur="#c62828"
        )
        self.poste = Poste.objects.create(
            nom="Manutention remorque planches",
            description="La remorque est trop haute.",
            auteur=self.alice,
            latitude=48.42,
            longitude=-4.55,
        )
        self.hier = timezone.localdate() - timedelta(days=1)
        self.revue = Revue.objects.create(
            date=self.hier, compte_rendu="Point complet de l'équipe."
        )
        self.revue.participants.set([self.alice, self.lea])
        self.revue.postes.set([self.poste])

    def donnees_revue(self, **modifs):
        donnees = {
            "date": timezone.localdate().isoformat(),
            "participants": [self.alice.id, self.lea.id],
            "compte_rendu": "Revue du mardi.",
        }
        donnees.update(modifs)
        return donnees

    def donnees_action(self, **modifs):
        donnees = {
            "intitule": "Regler la hauteur de la remorque",
            "description": "Ajouter un marchepied.",
            "responsable": self.alice.id,
            "echeance": (timezone.localdate() + timedelta(days=7)).isoformat(),
            "latitude": "",
            "longitude": "",
        }
        donnees.update(modifs)
        return donnees


class RevueAccesTests(RevueFixture):
    def test_creation_par_l_equipe(self):
        response = self.client.post(
            reverse("revue_creer"), self.donnees_revue()
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Revue.objects.count(), 2)

    def test_creation_sans_date_refusee(self):
        response = self.client.post(
            reverse("revue_creer"), self.donnees_revue(date="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Revue.objects.count(), 1)

    def test_acces_anonyme_redirige(self):
        self.client.logout()
        response = self.client.get(reverse("revues"))
        self.assertEqual(response.status_code, 302)

    def test_liste_et_detail(self):
        response = self.client.get(reverse("revues"))
        self.assertContains(response, "novembre")
        response = self.client.get(
            reverse("revue_detail", args=[self.revue.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Postes examinés")
        self.assertContains(response, "Manutention remorque planches")
        self.assertContains(response, "Lea")
        self.assertContains(response, "Point complet de")

    def test_modification(self):
        response = self.client.post(
            reverse("revue_modifier", args=[self.revue.pk]),
            self.donnees_revue(compte_rendu="Compte rendu revu."),
        )
        self.assertEqual(response.status_code, 302)
        self.revue.refresh_from_db()
        self.assertEqual(self.revue.compte_rendu, "Compte rendu revu.")


class PostesExaminesTests(RevueFixture):
    """L'ajout d'un poste passe par la revue (M2M), le retrait ne
    touche jamais au journal déjà consigné."""

    def setUp(self):
        super().setUp()
        self.vestiaire = Poste.objects.create(
            nom="Vestiaire moniteurs",
            description="La porte coince.",
            auteur=self.alice,
            latitude=48.43,
            longitude=-4.56,
        )

    def test_ajout_puis_retrait(self):
        response = self.client.post(
            reverse("revue_poste_ajouter", args=[self.revue.pk]),
            {"poste": self.vestiaire.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.vestiaire, self.revue.postes.all())

        response = self.client.post(
            reverse("revue_poste_retirer", args=[self.revue.pk, self.vestiaire.pk]),
            {},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(self.vestiaire, self.revue.postes.all())

    def test_le_journal_survit_au_retrait(self):
        ChangementSatisfaction.objects.create(
            revue=self.revue,
            poste=self.vestiaire,
            ancienne=None,
            nouvelle=self.a_ameliorer,
        )
        self.revue.postes.add(self.vestiaire)
        self.client.post(
            reverse("revue_poste_retirer", args=[self.revue.pk, self.vestiaire.pk]),
            {},
        )
        self.assertEqual(self.revue.changements.count(), 1)

    def test_ajout_depuis_get_sans_effet(self):
        self.client.get(
            reverse("revue_poste_ajouter", args=[self.revue.pk]),
            {"poste": self.vestiaire.pk},
        )
        self.assertNotIn(self.vestiaire, self.revue.postes.all())


class DecisionSatisfactionTests(RevueFixture):
    """Règle 3 : décision collégiale, journalisée, postes examinés
    uniquement, sans doublon si la valeur ne change pas."""

    def url_decision(self, poste=None):
        poste = poste or self.poste
        return reverse("revue_satisfaction", args=[self.revue.pk, poste.pk])

    def test_premiere_decision_journalisee(self):
        response = self.client.post(
            self.url_decision(), {"satisfaction": self.a_ameliorer.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.poste.refresh_from_db()
        self.assertEqual(self.poste.satisfaction, self.a_ameliorer)
        changement = ChangementSatisfaction.objects.get()
        self.assertIsNone(changement.ancienne)
        self.assertEqual(changement.nouvelle, self.a_ameliorer)
        self.assertEqual(changement.revue, self.revue)

    def test_changement_suivant_trace_ancienne_valeur(self):
        self.client.post(
            self.url_decision(), {"satisfaction": self.a_ameliorer.pk}
        )
        self.client.post(
            self.url_decision(), {"satisfaction": self.satisfaisant.pk}
        )
        self.poste.refresh_from_db()
        self.assertEqual(self.poste.satisfaction, self.satisfaisant)
        self.assertEqual(ChangementSatisfaction.objects.count(), 2)
        dernier = ChangementSatisfaction.objects.order_by("-quand").first()
        self.assertEqual(dernier.ancienne, self.a_ameliorer)
        self.assertEqual(dernier.nouvelle, self.satisfaisant)

    def test_meme_valeur_pas_de_doublon_au_journal(self):
        self.client.post(
            self.url_decision(), {"satisfaction": self.a_ameliorer.pk}
        )
        self.client.post(
            self.url_decision(), {"satisfaction": self.a_ameliorer.pk}
        )
        self.assertEqual(ChangementSatisfaction.objects.count(), 1)

    def test_decision_sur_poste_non_examine_refusee(self):
        hors_revue = Poste.objects.create(
            nom="Vestiaire moniteurs",
            description="La porte coince.",
            auteur=self.alice,
            latitude=48.43,
            longitude=-4.56,
        )
        response = self.client.post(
            self.url_decision(hors_revue),
            {"satisfaction": self.a_ameliorer.pk},
        )
        self.assertEqual(response.status_code, 404)
        hors_revue.refresh_from_db()
        self.assertIsNone(hors_revue.satisfaction)

    def test_valeur_inconnue_refusee(self):
        response = self.client.post(self.url_decision(), {"satisfaction": 999})
        self.assertEqual(response.status_code, 404)
        self.poste.refresh_from_db()
        self.assertIsNone(self.poste.satisfaction)


class ActionsEnRevueTests(RevueFixture):
    """Règle 5 : en revue, la création est collégiale (toute l'équipe
    identifiée) et l'action porte la trace de la revue ; hors revue,
    elle reste réservée à l'animateur."""

    def test_action_collegiale_meme_par_non_animateur(self):
        response = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(revue=self.revue.pk),
        )
        self.assertEqual(response.status_code, 302)
        action = Action.objects.get()
        self.assertEqual(action.revue, self.revue)
        self.assertEqual(action.poste, self.poste)

    def test_vue_depuis_revue_par_non_animateur(self):
        """Le lien de la revue porte ?revue=pk (GET), le POST le
        renvoie : les deux chemins aboutissent à la décision collégiale."""
        response = self.client.get(
            reverse("action_creer", args=[self.poste.pk]),
            {"revue": self.revue.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "revue du")

    def test_hors_revue_non_animateur_toujours_refuse(self):
        response = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Action.objects.count(), 0)

    def test_hors_revue_animateur_sans_revue(self):
        self.client.login(username="lea", password="mot de passe-123")
        self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(),
        )
        action = Action.objects.get()
        self.assertIsNone(action.revue)

    def test_revue_inconnue_refusee(self):
        response = self.client.post(
            reverse("action_creer", args=[self.poste.pk]),
            self.donnees_action(revue=999),
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_affiche_la_revue(self):
        action = Action.objects.create(
            poste=self.poste,
            intitule="Regler la hauteur de la remorque",
            responsable=self.alice,
            echeance=timezone.localdate() + timedelta(days=7),
            revue=self.revue,
        )
        response = self.client.get(reverse("action_detail", args=[action.pk]))
        self.assertContains(response, "revue du")
        self.assertContains(
            response, reverse("revue_detail", args=[self.revue.pk])
        )


class JournalImmuableTests(RevueFixture):
    def test_revue_insupprimable(self):
        with self.assertRaises(PermissionDenied):
            self.revue.delete()

    def test_changement_insupprimable(self):
        changement = ChangementSatisfaction.objects.create(
            revue=self.revue,
            poste=self.poste,
            ancienne=None,
            nouvelle=self.a_ameliorer,
        )
        with self.assertRaises(PermissionDenied):
            changement.delete()


class AffichageTests(RevueFixture):
    def test_journal_sur_la_revue(self):
        ChangementSatisfaction.objects.create(
            revue=self.revue,
            poste=self.poste,
            ancienne=None,
            nouvelle=self.a_ameliorer,
        )
        response = self.client.get(
            reverse("revue_detail", args=[self.revue.pk])
        )
        self.assertContains(response, "Décisions consignées")
        self.assertContains(response, "À améliorer")

    def test_historique_sur_le_poste(self):
        ChangementSatisfaction.objects.create(
            revue=self.revue,
            poste=self.poste,
            ancienne=None,
            nouvelle=self.a_ameliorer,
        )
        response = self.client.get(
            reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertContains(response, "Historique de satisfaction")
        self.assertContains(response, "À améliorer")

    def test_home_affiche_la_derniere_revue(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Dernière revue")
        self.assertContains(
            response, reverse("revue_detail", args=[self.revue.pk])
        )

    def test_repartitionsatisfaction_sur_home(self):
        self.poste.satisfaction = self.a_ameliorer
        self.poste.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "1 à améliorer")
