"""Tests M6 : plans de bâtiments — formes dessinées (Terra Draw) ou
images importées calées par 4 coins WGS84, affichés sur la carte sous
les marqueurs ; gestion réservée au staff (écran 6), étages côte à
côte jamais empilés. La suppression d'un plan reste possible : c'est
du contexte de travail, pas une trace d'amélioration."""
import json
import tempfile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import PlanBatiment, Utilisateur

# Dossier isolé pour l'écriture des fichiers de test : rien ne doit
# arriver dans le dossier du projet (la CI commite tout).
MEDIAS_TESTS = tempfile.mkdtemp(prefix="dudu-plans-tests-")

POLYGONE = {
    "type": "Polygon",
    "coordinates": [
        [
            [-4.56, 48.41],
            [-4.55, 48.41],
            [-4.55, 48.42],
            [-4.56, 48.42],
            [-4.56, 48.41],
        ]
    ],
}
COINS = [
    [-4.56, 48.42],
    [-4.55, 48.42],
    [-4.55, 48.41],
    [-4.56, 48.41],
]


def image_plan():
    """Un petit PNG joue le plan papier numérisé."""
    tampon = BytesIO()
    Image.new("RGB", (120, 80), (59, 125, 216)).save(tampon, format="PNG")
    return SimpleUploadedFile(
        "plan-test.png", tampon.getvalue(), content_type="image/png"
    )


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class PlanFixture(TestCase):
    """Zoé (staff), Alice (événementiel non staff), une image de
    plan prête à caler."""

    def setUp(self):
        self.zoe = Utilisateur.objects.create_user(
            "zoe", password="mot de passe-123", is_staff=True
        )
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.client.login(username="zoe", password="mot de passe-123")

    def plan_forme(self, **modifs):
        donnees = {"nom": "Hangar", "nature": "forme"}
        donnees.update(modifs)
        return PlanBatiment.objects.create(auteur=self.zoe, **donnees)

    def plan_image(self, **modifs):
        donnees = {"nom": "Hangar", "nature": "image"}
        donnees.update(modifs)
        return PlanBatiment.objects.create(
            auteur=self.zoe, fichier=image_plan(), **donnees
        )


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class ModeleTests(PlanFixture):
    """Les garde-fous du modèle : les deux natures ne se mélangent
    pas, l'image calée exige exactement 4 coins [lng, lat]."""

    def test_forme_avec_image_interdite(self):
        plan = PlanBatiment(
            auteur=self.zoe, nom="Hangar", nature="forme", fichier=image_plan()
        )
        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_forme_avec_coins_interdite(self):
        plan = PlanBatiment(
            auteur=self.zoe, nom="Hangar", nature="forme", coins=COINS
        )
        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_image_crees_avant_calage(self):
        """Le flux réel : un plan image naît sans coins (« à caler »),
        l'éditeur de calage les posera ensuite."""
        plan = PlanBatiment(
            auteur=self.zoe, nom="Hangar", nature="image", fichier=image_plan()
        )
        plan.full_clean()  # pas encore calé : c'est un état, pas une faute
        self.assertFalse(plan.est_complet())

    def test_coins_fautifs_invalide(self):
        for fautif in (COINS[:3], [[0, 0], [1, 1], "x"], "autre"):
            with self.assertRaises(ValidationError):
                plan = PlanBatiment(
                    auteur=self.zoe,
                    nom="Hangar",
                    nature="image",
                    fichier=image_plan(),
                    coins=fautif,
                )
                plan.full_clean()

    def test_couleur_fautive_invalide(self):
        with self.assertRaises(ValidationError):
            plan = PlanBatiment(
                auteur=self.zoe, nom="Hangar", nature="forme", couleur="bleu"
            )
            plan.full_clean()

    def test_etage_distinct_par_etiquette(self):
        """Spec : les étages se dessinent côte à côte, jamais
        empilés — l'étiquette dit lequel."""
        rdc = self.plan_forme(etiquette="rez-de-chaussée")
        etage = self.plan_forme(etiquette="étage")
        self.assertEqual(str(rdc), "Hangar — rez-de-chaussée")
        self.assertEqual(str(etage), "Hangar — étage")


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class AccesTests(PlanFixture):
    """Écran 6 : les plans se dessinent et se calent côté admin —
    réservé au staff (règle des écrans)."""

    def test_anonyme_redirige(self):
        self.client.logout()
        reponse = self.client.get(reverse("plans"))
        self.assertEqual(reponse.status_code, 302)

    def test_non_staff_refuse(self):
        self.client.logout()
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.get(reverse("plans"))
        self.assertEqual(reponse.status_code, 403)

    def test_staff_liste_les_plans(self):
        self.plan_forme()
        reponse = self.client.get(reverse("plans"))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Hangar")

    def test_lien_plans_absent_des_non_staff(self):
        self.client.logout()
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.get(reverse("carte"))
        self.assertNotContains(reponse, 'href="/plans/"')


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class CreationTests(PlanFixture):
    def test_forme_creee(self):
        reponse = self.client.post(
            reverse("plan_nouveau"),
            {"nom": "Hangar", "nature": "forme"},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(PlanBatiment.objects.count(), 1)
        plan = PlanBatiment.objects.first()
        self.assertEqual(plan.nature, "forme")
        self.assertEqual(plan.auteur, self.zoe)
        self.assertAlmostEqual(plan.opacite, 0.5)  # défaut : 50 %

    def test_image_creee_redirige_vers_calage(self):
        reponse = self.client.post(
            reverse("plan_nouveau"),
            {"nom": "Hangar", "nature": "image", "fichier": image_plan()},
        )
        self.assertRedirects(
            reponse, reverse("plan_calage", args=[PlanBatiment.objects.first().pk])
        )
        self.assertEqual(PlanBatiment.objects.count(), 1)

    def test_image_sans_fichier_refusee(self):
        reponse = self.client.post(
            reverse("plan_nouveau"),
            {"nom": "Hangar", "nature": "image"},
            follow=True,
        )
        self.assertEqual(PlanBatiment.objects.count(), 0)
        self.assertContains(
            reponse, "Importe une image (PNG/JPG)"
        )

    def test_modification_opacite(self):
        plan = self.plan_forme()
        reponse = self.client.post(
            reverse("plan_modifier", args=[plan.pk]),
            {
                "nom": plan.nom,
                "nature": "forme",
                "couleur": "#3b7dd8",
                "ordre": 0,
                "opacite": "0.8",
            },
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        plan.refresh_from_db()
        self.assertAlmostEqual(plan.opacite, 0.8)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class DessinTests(PlanFixture):
    def test_dessin_enregistre(self):
        plan = self.plan_forme()
        reponse = self.client.post(
            reverse("plan_dessin", args=[plan.pk]),
            {"forme": json.dumps(POLYGONE)},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.forme["type"], "Polygon")
        self.assertContains(reponse, "apparaît sur la carte")

    def test_dessin_illisible_refuse(self):
        plan = self.plan_forme()
        reponse = self.client.post(
            reverse("plan_dessin", args=[plan.pk]),
            {"forme": "pas du json"},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        plan.refresh_from_db()
        self.assertIsNone(plan.forme)
        self.assertContains(reponse, "illisible")

    def test_dessin_de_trace_non_polygone_refuse(self):
        plan = self.plan_forme()
        self.client.post(
            reverse("plan_dessin", args=[plan.pk]),
            {"forme": json.dumps({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})},
            follow=True,
        )
        plan.refresh_from_db()
        self.assertIsNone(plan.forme)

    def test_page_dessin_contient_terra_draw(self):
        plan = self.plan_forme()
        reponse = self.client.get(reverse("plan_dessin", args=[plan.pk]))
        self.assertContains(reponse, "vendor/terra-draw.umd.js")
        self.assertContains(reponse, "js/plan-dessin.js")

    def test_dessin_sur_plan_image_refuse(self):
        plan = self.plan_image()
        reponse = self.client.get(reverse("plan_dessin", args=[plan.pk]))
        self.assertEqual(reponse.status_code, 403)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class CalageTests(PlanFixture):
    def test_calage_enregistre(self):
        plan = self.plan_image()
        reponse = self.client.post(
            reverse("plan_calage", args=[plan.pk]),
            {"coins": json.dumps(COINS), "opacite": "0.7"},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.coins, COINS)
        self.assertAlmostEqual(plan.opacite, 0.7)

    def test_coins_incomplets_refuses(self):
        plan = self.plan_image()
        reponse = self.client.post(
            reverse("plan_calage", args=[plan.pk]),
            {"coins": json.dumps(COINS[:3]), "opacite": "0.7"},
            follow=True,
        )
        plan.refresh_from_db()
        self.assertIsNone(plan.coins)
        self.assertContains(reponse, "illisible")

    def test_calage_sur_plan_forme_refuse(self):
        plan = self.plan_forme()
        reponse = self.client.get(reverse("plan_calage", args=[plan.pk]))
        self.assertEqual(reponse.status_code, 403)

    def test_page_calage_contient_url_du_plan(self):
        plan = self.plan_image(coins=COINS)
        reponse = self.client.get(reverse("plan_calage", args=[plan.pk]))
        self.assertContains(reponse, "/medias/plans/")

    def test_calage_par_non_staff_refuse(self):
        self.client.logout()
        self.client.login(username="alice", password="mot de passe-123")
        plan = self.plan_image()
        reponse = self.client.post(
            reverse("plan_calage", args=[plan.pk]),
            {"coins": json.dumps(COINS), "opacite": "0.7"},
        )
        self.assertEqual(reponse.status_code, 403)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class CarteTests(PlanFixture):
    """La carte porte les plans : formes et images, sous les
    marqueurs (données sérialisées par json_script)."""

    def test_plans_dans_les_donnees_de_la_carte(self):
        self.client.login(username="zoe", password="mot de passe-123")
        self.plan_forme(forme=POLYGONE, etiquette="Hangar - rez")
        self.plan_image(coins=COINS)
        reponse = self.client.get(reverse("carte"))
        self.assertContains(reponse, "Hangar")
        self.assertContains(reponse, "Hangar - rez")
        self.assertContains(reponse, "/medias/plans/")

    def test_plan_incomplet_toujours_liste(self):
        """Même non dessiné, un plan vit dans la liste (badge « à
        dessiner ») — la carte, elle, attend sa forme."""
        self.plan_forme()
        reponse = self.client.get(reverse("plans"))
        self.assertContains(reponse, "à dessiner")


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class SuppressionTests(PlanFixture):
    """Un plan de bâtiment est du contexte de travail : supprimer un
    import erroné reste légitime (POST uniquement, staff)."""

    def test_suppression_par_staff(self):
        plan = self.plan_image(coins=COINS)
        nom_fichier = plan.fichier.name
        reponse = self.client.post(
            reverse("plan_supprimer", args=[plan.pk]), follow=True
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(PlanBatiment.objects.count(), 0)
        self.assertFalse(default_storage.exists(nom_fichier))

    def test_suppression_en_get_redirige(self):
        plan = self.plan_forme()
        reponse = self.client.get(reverse("plan_supprimer", args=[plan.pk]))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(PlanBatiment.objects.count(), 1)

    def test_suppression_par_non_staff_refuse(self):
        plan = self.plan_forme()
        self.client.logout()
        self.client.login(username="alice", password="mot de passe-123")
        reponse = self.client.post(reverse("plan_supprimer", args=[plan.pk]))
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(PlanBatiment.objects.count(), 1)
