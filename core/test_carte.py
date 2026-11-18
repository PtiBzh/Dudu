"""Tests M3 : carte — vue, mêmes filtres que la liste, position
obligatoire au clic, couleurs des marqueurs. Les tests sont
volontairement indépendants de la bibliothèque cartographique : ils
vérifient la page servie et les données sérialisées (json_script),
pas le rendu navigateur."""
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Action,
    Lieu,
    Poste,
    Utilisateur,
    ValeurFrequence,
    ValeurGravite,
    ValeurSatisfaction,
)


class CarteFixture(TestCase):
    """Alice connectée, un poste positionné, un poste sans position."""

    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.client.login(username="alice", password="mot de passe-123")
        self.lieu = Lieu.objects.create(nom="Hangar", ordre=1)
        self.gravite = ValeurGravite.objects.create(
            libelle="Elevee", ordre=1, couleur="#c62828"
        )
        self.frequence = ValeurFrequence.objects.create(
            libelle="Quotidienne", ordre=1
        )
        self.poste = Poste.objects.create(
            nom="Manutention remorque planches",
            description="La remorque est trop haute.",
            auteur=self.alice,
            lieu=self.lieu,
            gravite=self.gravite,
            frequence=self.frequence,
            origine=Poste.Origine.CONSTAT,
            latitude=48.42,
            longitude=-4.55,
        )
        self.poste_sans_position = Poste.objects.create(
            nom="Accueil des gens",
            description="Le brancard frotte a la porte.",
            auteur=self.alice,
            lieu=self.lieu,
            gravite=self.gravite,
            frequence=self.frequence,
            origine=Poste.Origine.CONSTAT,
        )

    def donnees_poste(self, **modifs):
        """Données de saisie d'un poste positionné (comme le_formulaire
        de la mini-carte les envoie)."""
        donnees = {
            "nom": "Vestiaire moniteurs",
            "description": "Patere qui se decroche.",
            "lieu": self.lieu.id,
            "gravite": self.gravite.id,
            "frequence": self.frequence.id,
            "origine": Poste.Origine.CONSTAT,
            "latitude": "48.4300",
            "longitude": "-4.5600",
        }
        donnees.update(modifs)
        return donnees


class CarteVueTests(CarteFixture):
    def test_acces_connecte(self):
        response = self.client.get(reverse("carte"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "boite-carte")

    def test_acces_anonyme_redirige(self):
        self.client.logout()
        response = self.client.get(reverse("carte"))
        self.assertEqual(response.status_code, 302)

    def test_poste_positionne_present(self):
        response = self.client.get(reverse("carte"))
        self.assertContains(response, "Manutention remorque planches")
        self.assertContains(response, "48.42")

    def test_poste_sans_position_absent(self):
        response = self.client.get(reverse("carte"))
        self.assertNotContains(response, "Accueil des gens")

    def test_recherche_filtrer_la_carte(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        response = self.client.get(reverse("carte"), {"q": "Manutention"})
        self.assertContains(response, "Manutention remorque planches")
        self.assertNotContains(response, "Vestiaire moniteurs")

    def test_archives_absentes_par_defaut(self):
        self.poste.archive = True
        self.poste.save()
        response = self.client.get(reverse("carte"))
        self.assertNotContains(response, "Manutention remorque planches")

    def test_archives_visibles_si_demande(self):
        self.poste.archive = True
        self.poste.save()
        response = self.client.get(reverse("carte"), {"archivage": "archives"})
        self.assertContains(response, "Manutention remorque planches")

    def test_action_ouverte_visible(self):
        Action.objects.create(
            poste=self.poste,
            intitule="Regler la hauteur de la remorque",
            description="Ajouter une marche.",
            responsable=self.alice,
            echeance=timezone.localdate() + timedelta(days=7),
            statut=Action.Statut.A_FAIRE,
            latitude=48.42,
            longitude=-4.55,
        )
        response = self.client.get(reverse("carte"))
        self.assertContains(response, "/actions/1/")

    def test_action_fermee_absente(self):
        Action.objects.create(
            poste=self.poste,
            intitule="Regler la hauteur de la remorque",
            description="Ajouter une marche.",
            responsable=self.alice,
            echeance=timezone.localdate(),
            statut=Action.Statut.FAITE,
            latitude=48.42,
            longitude=-4.55,
        )
        response = self.client.get(reverse("carte"))
        self.assertNotContains(response, "/actions/1/")
        self.assertNotContains(response, "Regler la hauteur de la remorque")

    def test_lien_vers_la_fiche(self):
        response = self.client.get(reverse("carte"))
        self.assertContains(response, "/postes/%d/" % self.poste.pk)

    def test_poste_cible_dans_attribut(self):
        response = self.client.get(reverse("carte"), {"poste": self.poste.pk})
        self.assertContains(response, 'data-poste="%d"' % self.poste.pk)


class PositionObligatoireTests(CarteFixture):
    def test_creation_sans_position_refusee(self):
        response = self.client.post(
            reverse("poste_creer"),
            self.donnees_poste(latitude="", longitude=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "clique sur la carte")
        self.assertEqual(Poste.objects.count(), 2)

    def test_edition_sans_position_refusee(self):
        response = self.client.post(
            reverse("poste_modifier", args=[self.poste.pk]),
            self.donnees_poste(latitude="", longitude=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "clique sur la carte")
        self.poste.refresh_from_db()
        self.assertEqual(self.poste.latitude, 48.42)

    def test_ancien_poste_jamais_positionne_tolere(self):
        """Un poste saisi avant la carte (M1/M2) reste modifiable sans
        position ; rien n'est cassé, rien n'est inventé."""
        response = self.client.post(
            reverse("poste_modifier", args=[self.poste_sans_position.pk]),
            self.donnees_poste(latitude="", longitude=""),
        )
        self.assertEqual(response.status_code, 302)
        self.poste_sans_position.refresh_from_db()
        self.assertIsNone(self.poste_sans_position.latitude)

    def test_latitude_hors_bornes_refusee(self):
        response = self.client.post(
            reverse("poste_creer"), self.donnees_poste(latitude="120")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "entre -90 et 90")
        self.assertEqual(Poste.objects.count(), 2)

    def test_creation_avec_position_reussie(self):
        response = self.client.post(
            reverse("poste_creer"), self.donnees_poste()
        )
        self.assertEqual(response.status_code, 302)
        poste = Poste.objects.get(nom="Vestiaire moniteurs")
        self.assertAlmostEqual(poste.latitude, 48.43)
        self.assertAlmostEqual(poste.longitude, -4.56)

    def test_suppression_toujours_impossible(self):
        with self.assertRaises(PermissionDenied):
            self.poste.delete()


class CouleursTests(CarteFixture):
    def test_couleur_gravite_transmise(self):
        response = self.client.get(reverse("carte"))
        self.assertContains(response, "#c62828")

    def test_couleur_satisfaction_en_halo(self):
        satisfaction = ValeurSatisfaction.objects.create(
            libelle="Satisfaisant", ordre=1, couleur="#2e7d32"
        )
        self.poste.satisfaction = satisfaction
        self.poste.save()
        response = self.client.get(reverse("carte"))
        self.assertContains(response, "#2e7d32")

    def test_poste_sans_cotation_sans_couleur(self):
        self.poste.gravite = None
        self.poste.save()
        response = self.client.get(reverse("carte"))
        self.assertNotContains(response, "#c62828")
