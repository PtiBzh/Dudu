"""Tests du socle M0 : comptes, rôle animateur, authentification."""
from django.test import TestCase

from .models import Utilisateur


class UtilisateurTests(TestCase):
    def test_nouveau_compte_non_animateur(self):
        """Par défaut, personne n'est animateur : le rôle se donne
        explicitement."""
        u = Utilisateur.objects.create_user("alice", password="mot de passe-123")
        self.assertFalse(u.is_animateur)

    def test_str_affiche_le_nom_complet(self):
        u = Utilisateur.objects.create_user("alice", password="mot de passe-123")
        u.first_name, u.last_name = "Alice", "Dupont"
        self.assertEqual(str(u), "Alice Dupont")

    def test_str_repli_sur_pseudo_sans_nom(self):
        u = Utilisateur.objects.create_user("alice", password="mot de passe-123")
        self.assertEqual(str(u), "alice")


class AuthentificationTests(TestCase):
    def test_accueil_anonyme_redirige_vers_connexion(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("connexion", reponse["Location"])

    def test_connexion_puis_accueil(self):
        Utilisateur.objects.create_user("alice", password="mot de passe-123")
        self.assertTrue(
            self.client.login(username="alice", password="mot de passe-123")
        )
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Dudu")
        self.assertContains(reponse, "alice")

    def test_mauvais_mot_de_passe_refuse(self):
        Utilisateur.objects.create_user("alice", password="mot de passe-123")
        self.assertFalse(
            self.client.login(username="alice", password=" faux ")
        )

    def test_deconnexion_renvoie_vers_connexion(self):
        Utilisateur.objects.create_user("alice", password="mot de passe-123")
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.post("/deconnexion/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("connexion", reponse["Location"])
