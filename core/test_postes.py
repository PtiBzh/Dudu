"""Tests M1 : postes — création libre, filtres, cotation santé/sécurité,
édition tracée, archivage (jamais de suppression)."""
from django.urls import reverse
from django.test import TestCase

from .models import (
    EditionPoste,
    Lieu,
    Poste,
    Utilisateur,
    ValeurFrequence,
    ValeurGravite,
    ValeurSatisfaction,
)


class PosteFixture(TestCase):
    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.client.login(username="alice", password="mot de passe-123")
        self.lieu = Lieu.objects.create(nom="Hangar", ordre=1)
        self.gravite = ValeurGravite.objects.create(libelle="Faible", ordre=1)
        self.frequence = ValeurFrequence.objects.create(
            libelle="Quotidienne", ordre=1
        )

    def donnees_poste(self, **modifs):
        donnees = {
            "nom": "Manutention remorque planches",
            "description": "La remorque est trop haute, on se cogne la tête.",
            "lieu": self.lieu.id,
            "gravite": self.gravite.id,
            "frequence": self.frequence.id,
            "origine": Poste.Origine.CONSTAT,
            # Position obligatoire depuis M3 (choisie sur la mini-carte).
            "latitude": "48.4200",
            "longitude": "-4.5500",
        }
        donnees.update(modifs)
        return donnees


class CreationPosteTests(PosteFixture):
    def test_creation_de_poste(self):
        reponse = self.client.post(
            reverse("poste_creer"), self.donnees_poste()
        )
        self.assertRedirects(
            reponse, reverse("poste_detail", args=[Poste.objects.first().pk])
        )
        poste = Poste.objects.get(nom="Manutention remorque planches")
        self.assertEqual(poste.auteur, self.alice)
        self.assertEqual(poste.origine, Poste.Origine.CONSTAT)
        self.assertFalse(poste.archive)
        self.assertEqual(poste.lieu, self.lieu)
        self.assertEqual(poste.gravite, self.gravite)
        self.assertEqual(poste.frequence, self.frequence)

    def test_creation_anonyme_refusee(self):
        self.client.logout()
        reponse = self.client.post(
            reverse("poste_creer"), self.donnees_poste()
        )
        self.assertEqual(reponse.status_code, 302)  # vers la connexion

    def test_satisfaction_absente_du_formulaire(self):
        """Règle 3 : la satisfaction se décide en revue, pas à la saisie."""
        reponse = self.client.get(reverse("poste_creer"))
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, 'name="satisfaction"')

    def test_origine_presqu_accident(self):
        reponse = self.client.post(
            reverse("poste_creer"),
            self.donnees_poste(origine=Poste.Origine.PRESQU_ACCIDENT),
        )
        self.assertEqual(reponse.status_code, 302)
        poste = Poste.objects.first()
        self.assertEqual(poste.origine, Poste.Origine.PRESQU_ACCIDENT)


class ListePosteTests(PosteFixture):
    def test_le_poste_apparait(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        reponse = self.client.get(reverse("postes"))
        self.assertContains(reponse, "Manutention remorque planches")

    def test_filtre_par_lieu(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        parc = Lieu.objects.create(nom="Parc", ordre=2)
        self.client.post(
            reverse("poste_creer"),
            self.donnees_poste(nom="Accueil des gens", lieu=parc.id),
        )
        reponse = self.client.get(reverse("postes"), {"lieu": parc.id})
        self.assertContains(reponse, "Accueil des gens")
        self.assertNotContains(reponse, "Manutention remorque planches")

    def test_les_filtres_relancent_tout_seuls(self):
        """Listes déroulantes et recherche appliquées sans bouton
        Filtrer : le socle js/filtres.js est là, le bouton n'y est
        plus. La recherche texte part après une micro-pause."""
        reponse = self.client.get(reverse("postes"))
        self.assertContains(reponse, "js/filtres.js")
        self.assertNotContains(reponse, '<button type="submit">Filtrer')

    def test_recherche_texte(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        reponse = self.client.get(reverse("postes"), {"q": "vestiaire"})
        self.assertNotContains(reponse, "Manutention remorque planches")
        reponse = self.client.get(reverse("postes"), {"q": "remorque"})
        self.assertContains(reponse, "Manutention remorque planches")


class EditionPosteTests(PosteFixture):
    def creer(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        return Poste.objects.first()

    def test_l_auteur_peut_modifier(self):
        poste = self.creer()
        reponse = self.client.post(
            reverse("poste_modifier", args=[poste.pk]),
            self.donnees_poste(nom="Manutention remorque planches — v2"),
        )
        self.assertRedirects(reponse, reverse("poste_detail", args=[poste.pk]))
        poste.refresh_from_db()
        self.assertEqual(poste.nom, "Manutention remorque planches — v2")

    def test_toute_edition_est_tracee(self):
        """Règle 4 : « modifiée par X le Y »."""
        poste = self.creer()
        self.client.post(
            reverse("poste_modifier", args=[poste.pk]), self.donnees_poste()
        )
        self.assertEqual(EditionPoste.objects.count(), 1)
        trace = EditionPoste.objects.first()
        self.assertEqual(trace.qui, self.alice)
        self.assertEqual(trace.poste, poste)

    def test_utilisateur_quelconque_ne_peut_pas_modifier(self):
        poste = self.creer()
        Utilisateur.objects.create_user("bob", password="mot de passe-123")
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.client.post(
            reverse("poste_modifier", args=[poste.pk]), self.donnees_poste()
        )
        self.assertEqual(reponse.status_code, 403)

    def test_l_animateur_peut_modifier(self):
        poste = self.creer()
        Utilisateur.objects.create_user(
            "lea", password="mot de passe-123", is_animateur=True
        )
        self.client.login(username="lea", password="mot de passe-123")
        reponse = self.client.post(
            reverse("poste_modifier", args=[poste.pk]), self.donnees_poste()
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            EditionPoste.objects.first().qui.username,
            "lea",
        )


class ArchivagePosteTests(PosteFixture):
    def test_archivage_par_l_animateur(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        poste = Poste.objects.first()
        Utilisateur.objects.create_user(
            "lea", password="mot de passe-123", is_animateur=True
        )
        self.client.login(username="lea", password="mot de passe-123")
        self.client.post(reverse("poste_archiver", args=[poste.pk]))
        poste.refresh_from_db()
        self.assertTrue(poste.archive)

    def test_archive_disparait_de_la_liste_defaut(self):
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        poste = Poste.objects.first()
        poste.archive = True
        poste.save()
        reponse = self.client.get(reverse("postes"))
        self.assertNotContains(reponse, "Manutention remorque planches")
        # … mais reste consultable via le filtre « archives »
        reponse = self.client.get(reverse("postes"), {"archivage": "archives"})
        self.assertContains(reponse, "Manutention remorque planches")

    def test_pas_de_suppression_possible(self):
        """Règle 1 : rien ne disparaît — le modèle lui-même refuse
        la suppression (les vues ne l'exposent pas, l'admin l'interdit)."""
        self.client.post(reverse("poste_creer"), self.donnees_poste())
        poste = Poste.objects.first()
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            poste.delete()
