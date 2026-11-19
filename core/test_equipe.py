"""Tests M8 : équipe et paramètres du club — pages intégrées réservées
aux animateurs (comptes, rôles, listes de valeurs, réglages de carte).
"""
from django.test import TestCase
from django.urls import reverse

from .forms import ReglagesForm
from .models import (
    Lieu,
    Poste,
    Reglages,
    Utilisateur,
    ValeurGravite,
)


class EquipeFixture(TestCase):
    """Léa anime, Bob n'a aucun rôle, Sheela est staff (secrétariat)."""

    def setUp(self):
        self.lea = Utilisateur.objects.create_user(
            "lea",
            password="mot de passe-123",
            first_name="Léa",
            is_animateur=True,
        )
        self.bob = Utilisateur.objects.create_user(
            "bob", password="mot de passe-123"
        )
        self.sheela = Utilisateur.objects.create_user(
            "sheela", password="mot de passe-123", is_staff=True
        )
        self.client.login(username="lea", password="mot de passe-123")


class AccesTests(EquipeFixture):
    def test_non_animateur_refuse(self):
        self.client.login(username="bob", password="mot de passe-123")
        for nom in ("equipe", "parametres"):
            reponse = self.client.get(reverse(nom))
            self.assertEqual(reponse.status_code, 403)

    def test_animateur_voit_les_pages(self):
        for nom in ("equipe", "parametres"):
            reponse = self.client.get(reverse(nom))
            self.assertEqual(reponse.status_code, 200)

    def test_navigation_animateur(self):
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.client.get(reverse("home"))
        self.assertNotContains(reponse, "Paramètres")
        self.client.login(username="lea", password="mot de passe-123")
        reponse = self.client.get(reverse("home"))
        self.assertContains(reponse, "Équipe")
        self.assertContains(reponse, "Paramètres")


class ComptesTests(EquipeFixture):
    def test_page_equipe_liste_les_comptes(self):
        reponse = self.client.get(reverse("equipe"))
        self.assertContains(reponse, "lea")
        self.assertContains(reponse, "bob")

    def test_cree_un_compte_qui_se_connecte(self):
        reponse = self.client.post(
            reverse("equipe_creer"),
            {
                "username": "nour",
                "first_name": "Nour",
                "last_name": "Kervadec",
                "mot_de_passe": "mot de passe-123",
                "is_animateur": "on",
            },
        )
        self.assertRedirects(reponse, reverse("equipe"))
        nour = Utilisateur.objects.get(username="nour")
        self.assertTrue(nour.check_password("mot de passe-123"))
        self.assertTrue(nour.is_animateur)
        self.client.login(username="nour", password="mot de passe-123")

    def test_identifiant_deja_pris_refuse(self):
        reponse = self.client.post(
            reverse("equipe_creer"),
            {"username": "bob", "mot_de_passe": "mot de passe-123"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "déjà pris")
        self.assertEqual(
            Utilisateur.objects.filter(username__iexact="bob").count(), 1
        )

    def test_change_le_mot_de_passe(self):
        reponse = self.client.post(
            reverse("equipe_modifier", args=[self.bob.pk]),
            {
                "username": "bob",
                "is_animateur": "on",
                "is_active": "on",
                "nouveau_mot_de_passe": "autre mot passe-45",
            },
        )
        self.assertRedirects(reponse, reverse("equipe"))
        self.bob.refresh_from_db()
        self.assertTrue(self.bob.check_password("autre mot passe-45"))
        self.assertTrue(self.bob.is_animateur)

    def test_mot_de_passe_vide_inchange(self):
        self.client.post(
            reverse("equipe_modifier", args=[self.bob.pk]),
            {
                "username": "bob",
                "is_active": "on",
                "nouveau_mot_de_passe": "",
            },
        )
        self.bob.refresh_from_db()
        self.assertTrue(self.bob.check_password("mot de passe-123"))
        self.assertFalse(self.bob.is_animateur)

    def test_animateur_ne_se_demote_pas(self):
        reponse = self.client.post(
            reverse("equipe_modifier", args=[self.lea.pk]),
            {
                "username": "lea",
                "is_active": "on",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "ne se retire pas")
        self.lea.refresh_from_db()
        self.assertTrue(self.lea.is_animateur)

    def test_non_staff_ne_modifie_pas_le_staff(self):
        reponse = self.client.get(
            reverse("equipe_modifier", args=[self.sheela.pk])
        )
        self.assertEqual(reponse.status_code, 403)


class ListesValeursTests(EquipeFixture):
    def test_parametres_liste_les_quatre_sections(self):
        reponse = self.client.get(reverse("parametres"))
        self.assertContains(reponse, "Lieux du club")
        self.assertContains(reponse, "Gravités potentielles")
        # « d'exposition » : l'apostrophe est échappée en HTML (&#x27;),
        # on ne cherche donc que le début du titre.
        self.assertContains(reponse, "Fréquences d")
        self.assertContains(reponse, "Statuts de satisfaction")

    def test_ajoute_une_gravite(self):
        reponse = self.client.post(
            reverse("parametres_valeur_ajouter", args=["gravites"]),
            {"libelle": "Dramatique", "ordre": "4", "couleur": "#4a148c"},
        )
        self.assertRedirects(reponse, reverse("parametres"))
        self.assertTrue(
            ValeurGravite.objects.filter(libelle="Dramatique").exists()
        )

    def test_modifie_une_gravite(self):
        gravite = ValeurGravite.objects.create(
            libelle="Passagère", ordre=1, couleur="#111111"
        )
        reponse = self.client.post(
            reverse("parametres_valeur_modifier", args=["gravites", gravite.pk]),
            {"libelle": "Passagère", "ordre": "7", "couleur": "#222222"},
        )
        self.assertRedirects(reponse, reverse("parametres"))
        gravite.refresh_from_db()
        self.assertEqual(gravite.ordre, 7)

    def test_supprime_une_valeur_libre(self):
        gravite = ValeurGravite.objects.create(
            libelle="Fantôme", ordre=9, couleur="#000000"
        )
        reponse = self.client.post(
            reverse("parametres_valeur_supprimer", args=["gravites", gravite.pk])
        )
        self.assertRedirects(reponse, reverse("parametres"))
        self.assertFalse(ValeurGravite.objects.filter(pk=gravite.pk).exists())

    def test_valeur_utilisee_ne_disparait_pas(self):
        gravite = ValeurGravite.objects.create(
            libelle="Énorme", ordre=5, couleur="#000000"
        )
        Poste.objects.create(
            nom="Porter les planches",
            auteur=self.lea,
            gravite=gravite,
            latitude=48.42,
            longitude=-4.55,
        )
        reponse = self.client.post(
            reverse("parametres_valeur_supprimer", args=["gravites", gravite.pk])
        )
        self.assertRedirects(reponse, reverse("parametres"))
        self.assertTrue(ValeurGravite.objects.filter(pk=gravite.pk).exists())


class ReglagesCarteTests(EquipeFixture):
    def test_reglages_inities_depuis_env(self):
        courants = Reglages.charge()
        self.assertTrue(0.0 < courants.centre_latitude < 90.0)

    def test_change_le_centre_et_le_zoom(self):
        reponse = self.client.post(
            reverse("parametres_carte"),
            {
                "centre_latitude": "47.797593",
                "centre_longitude": "-4.212860",
                "zoom_carte": "15",
            },
        )
        self.assertRedirects(reponse, reverse("parametres"))
        courants = Reglages.charge()
        self.assertAlmostEqual(courants.centre_latitude, 47.797593)
        self.assertEqual(courants.zoom_carte, 15)

    def test_la_carte_suit_les_reglages(self):
        self.client.post(
            reverse("parametres_carte"),
            {
                "centre_latitude": "47.797593",
                "centre_longitude": "-4.212860",
                "zoom_carte": "15",
            },
        )
        reponse = self.client.get(reverse("carte"))
        self.assertContains(reponse, 'data-lat="47.797593"')
        self.assertContains(reponse, 'data-lng="-4.212860"')
        self.assertContains(reponse, 'data-zoom="15"')

    def test_zoom_decimal_accepte(self):
        """La mini-carte écrit un zoom à une décimale : le réglage
        l'accepte et toutes les cartes partent à ce zoom exact."""
        reponse = self.client.post(
            reverse("parametres_carte"),
            {
                "centre_latitude": "47.797593",
                "centre_longitude": "-4.212860",
                "zoom_carte": "14.6",
            },
        )
        self.assertRedirects(reponse, reverse("parametres"))
        courants = Reglages.charge()
        self.assertAlmostEqual(courants.zoom_carte, 14.6)
        reponse = self.client.get(reverse("carte"))
        self.assertContains(reponse, 'data-zoom="14.6"')

    def test_le_champ_zoom_ne_bloque_pas_les_decimales(self):
        """Sans step="any", la validation HTML5 refuse 14,6 avant même
        d'atteindre le serveur."""
        formulaire = ReglagesForm()
        self.assertEqual(
            formulaire["zoom_carte"].field.widget.attrs["step"], "any"
        )

    def test_latitude_folle_refusee(self):
        reponse = self.client.post(
            reverse("parametres_carte"),
            {
                "centre_latitude": "120",
                "centre_longitude": "-4.2",
                "zoom_carte": "15",
            },
        )
        self.assertContains(reponse, " entre -90 et 90 ")
        courants = Reglages.charge()
        self.assertNotAlmostEqual(courants.centre_latitude, 120)


class ReordonnancementTests(EquipeFixture):
    """Paramètres : l'ordre se règle en déposant les lignes — le
    serveur réécrit les rangs depuis la liste des identifiants, et
    refuse tout ce qui ne colle pas (rien ne disparaît)."""

    def test_la_page_porte_le_prochain_ordre(self):
        """Le jeu par défaut est en place : la prochaine gravité se
        rangera juste après la plus haute."""
        dernier = ValeurGravite.objects.order_by("-ordre").first()
        reponse = self.client.get(reverse("parametres"))
        self.assertContains(
            reponse, f'name="ordre" value="{dernier.ordre + 1}"'
        )

    def test_la_glisse_reecrit_les_rangs(self):
        faibles = ValeurGravite.objects.create(
            libelle="Faible", ordre=1, couleur="#111111"
        )
        enormes = ValeurGravite.objects.create(
            libelle="Énorme", ordre=2, couleur="#222222"
        )
        graves = ValeurGravite.objects.create(
            libelle="Grave", ordre=3, couleur="#333333"
        )
        reponse = self.client.post(
            reverse("parametres_ordre", args=["gravites"]),
            {
                "ordre": ",".join(
                    str(pk) for pk in (graves.pk, faibles.pk, enormes.pk)
                )
            },
        )
        self.assertRedirects(reponse, reverse("parametres"))
        faibles.refresh_from_db()
        enormes.refresh_from_db()
        graves.refresh_from_db()
        self.assertEqual(graves.ordre, 1)
        self.assertEqual(faibles.ordre, 2)
        self.assertEqual(enormes.ordre, 3)

    def test_identifiant_inconnu_refuse(self):
        gravite = ValeurGravite.objects.create(
            libelle="Passagère", ordre=1, couleur="#111111"
        )
        reponse = self.client.post(
            reverse("parametres_ordre", args=["gravites"]),
            {"ordre": "999"},
            follow=True,
        )
        self.assertContains(reponse, "Réordonnancement refusé")
        gravite.refresh_from_db()
        self.assertEqual(gravite.ordre, 1)

    def test_identifiant_en_double_refuse(self):
        gravite = ValeurGravite.objects.create(
            libelle="Passagère", ordre=1, couleur="#111111"
        )
        reponse = self.client.post(
            reverse("parametres_ordre", args=["gravites"]),
            {"ordre": f"{gravite.pk},{gravite.pk}"},
            follow=True,
        )
        self.assertContains(reponse, "Réordonnancement refusé")
        gravite.refresh_from_db()
        self.assertEqual(gravite.ordre, 1)

    def test_beurk_illisible_refuse(self):
        gravite = ValeurGravite.objects.create(
            libelle="Passagère", ordre=1, couleur="#111111"
        )
        reponse = self.client.post(
            reverse("parametres_ordre", args=["gravites"]),
            {"ordre": "des chevaux"},
            follow=True,
        )
        self.assertContains(reponse, "Réordonnancement refusé")
        gravite.refresh_from_db()
        self.assertEqual(gravite.ordre, 1)

    def test_non_animateur_refuse(self):
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.client.post(reverse("parametres_ordre", args=["gravites"]), {"ordre": ""})
        self.assertEqual(reponse.status_code, 403)

    def test_liste_inconnue_refuse(self):
        reponse = self.client.post(
            reverse("parametres_ordre", args=["nimporte"]), {"ordre": "1"}
        )
        self.assertEqual(reponse.status_code, 404)

    def test_lieux_se_reordonnent_aussi(self):
        """Les lieux ont le même ordre d'affichage : la poignée y
        fonctionne pareil."""
        hangar = Lieu.objects.create(nom="Hangar", ordre=1)
        parc = Lieu.objects.create(nom="Parc", ordre=2)
        reponse = self.client.post(
            reverse("parametres_ordre", args=["lieux"]),
            {"ordre": f"{parc.pk},{hangar.pk}"},
        )
        self.assertRedirects(reponse, reverse("parametres"))
        hangar.refresh_from_db()
        parc.refresh_from_db()
        self.assertEqual(parc.ordre, 1)
        self.assertEqual(hangar.ordre, 2)
