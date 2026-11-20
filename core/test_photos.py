"""Tests M5 : photos avant/après — compression à l'upload (~1600 px
JPEG, spec technique), « avant » au poste / « après » à l'action,
règle des écrans n° 5 (avertissement non bloquant quand on clôture
sans photo), vue avant/après sur le poste et en revue."""
import os
import tempfile
from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Action, Photo, Poste, Revue, Utilisateur

# Dossier isolé pour l'écriture des fichiers de test : rien ne doit
# arriver dans le dossier du projet (la CI commite tout).
MEDIAS_TESTS = tempfile.mkdtemp(prefix="dudu-photos-tests-")


def image_test(taille=(2400, 1600), couleur=(200, 60, 60), fmt="JPEG"):
    image = Image.new("RGB", taille, couleur)
    tampon = BytesIO()
    image.save(tampon, format=fmt)
    return SimpleUploadedFile(
        "photo-test.jpg",
        tampon.getvalue(),
        content_type="image/jpeg",
    )


class PhotoFixture(TestCase):
    """Alice (responsable de l'action), Bob (tiers), Lea (animatrice),
    un poste positionné, une action ouverte."""

    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.bob = Utilisateur.objects.create_user(
            "bob", password="mot de passe-123"
        )
        self.lea = Utilisateur.objects.create_user(
            "lea", password="mot de passe-123", is_animateur=True
        )
        self.client.login(username="alice", password="mot de passe-123")
        self.poste = Poste.objects.create(
            nom="Manutention remorque planches",
            description="La remorque est trop haute.",
            auteur=self.alice,
            latitude=48.42,
            longitude=-4.55,
        )
        self.action = Action.objects.create(
            poste=self.poste,
            intitule="Regler la hauteur de la remorque",
            description="Ajouter un marchepied.",
            responsable=self.alice,
            echeance=timezone.localdate() + timedelta(days=7),
        )
        self.hier = timezone.localdate() - timedelta(days=1)

    def ajouter_photo_avant(self, **modifs):
        return self.client.post(
            reverse("poste_photo_ajouter", args=[self.poste.pk]),
            {"fichier": image_test(**modifs)},
        )

    def ajouter_photo_apres(self, **modifs):
        return self.client.post(
            reverse("action_photo_ajouter", args=[self.action.pk]),
            {"fichier": image_test(**modifs)},
        )


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class CompressionTests(PhotoFixture):
    def test_grande_image_reduite(self):
        self.ajouter_photo_avant(taille=(2400, 1600))
        photo = Photo.objects.get()
        with Image.open(photo.fichier.path) as image:
            self.assertLessEqual(max(image.size), 1600)
            self.assertEqual(image.format, "JPEG")

    def test_petite_image_pas_agrandie(self):
        self.ajouter_photo_avant(taille=(1200, 800))
        photo = Photo.objects.get()
        with Image.open(photo.fichier.path) as image:
            self.assertEqual(image.size, (1200, 800))

    def test_poids_contenu(self):
        """Une photo de test recompressée doit rester nettement plus
        légère qu'un fichier non compressé de même taille."""
        self.ajouter_photo_avant(taille=(4000, 3000))
        photo = Photo.objects.get()
        self.assertLess(photo.fichier.size, 500_000)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class PhotoAvantTests(PhotoFixture):
    def test_membre_de_l_equipe_ajoute(self):
        reponse = self.ajouter_photo_avant()
        self.assertEqual(reponse.status_code, 302)
        photo = Photo.objects.get()
        self.assertEqual(photo.type, Photo.Type.AVANT)
        self.assertEqual(photo.poste, self.poste)
        self.assertEqual(photo.auteur, self.alice)

    def test_anonyme_redirige(self):
        self.client.logout()
        reponse = self.client.post(
            reverse("poste_photo_ajouter", args=[self.poste.pk]), {}
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)

    def test_sans_fichier_aucune_photo(self):
        reponse = self.client.post(
            reverse("poste_photo_ajouter", args=[self.poste.pk]), {}
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class PhotoApresTests(PhotoFixture):
    def test_tiers_refuse(self):
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.ajouter_photo_apres()
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(Photo.objects.count(), 0)

    def test_responsable_ajoute(self):
        reponse = self.ajouter_photo_apres()
        self.assertEqual(reponse.status_code, 302)
        photo = Photo.objects.get()
        self.assertEqual(photo.type, Photo.Type.APRES)
        self.assertEqual(photo.action, self.action)
        self.assertEqual(photo.auteur, self.alice)

    def test_animatrice_ajoute(self):
        self.client.login(username="lea", password="mot de passe-123")
        self.ajouter_photo_apres()
        self.assertEqual(Photo.objects.count(), 1)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class SuppressionPhotoTests(PhotoFixture):
    """Une photo importée par erreur se supprime : quiconque est
    connecté, en POST ; le fichier part avec la fiche."""

    def test_suppression_de_l_avant_revient_au_poste(self):
        self.ajouter_photo_avant()
        photo = Photo.objects.get()
        chemin = photo.fichier.path
        reponse = self.client.post(
            reverse("photo_supprimer", args=[photo.pk])
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            reponse.url, reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertEqual(Photo.objects.count(), 0)
        self.assertFalse(os.path.exists(chemin))

    def test_suppression_de_l_apres_revient_a_l_action(self):
        self.ajouter_photo_apres()
        photo = Photo.objects.get()
        reponse = self.client.post(
            reverse("photo_supprimer", args=[photo.pk])
        )
        self.assertEqual(
            reponse.url, reverse("action_detail", args=[self.action.pk])
        )
        self.assertEqual(Photo.objects.count(), 0)

    def test_tier_supprime_aussi(self):
        """La suppression n'est pas réservée à l'auteur : l'essentiel
        est de retomber sur une photo erronée, peu importe qui."""
        self.ajouter_photo_avant()
        self.client.login(username="bob", password="mot de passe-123")
        reponse = self.client.post(
            reverse("photo_supprimer", args=[Photo.objects.get().pk])
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)

    def test_anonyme_redirige(self):
        self.ajouter_photo_avant()
        self.client.logout()
        reponse = self.client.post(
            reverse("photo_supprimer", args=[Photo.objects.get().pk])
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Photo.objects.count(), 1)

    def test_get_ne_supprime_pas(self):
        self.ajouter_photo_avant()
        photo = Photo.objects.get()
        reponse = self.client.get(reverse("photo_supprimer", args=[photo.pk]))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(Photo.objects.count(), 1)


class ClotureTests(PhotoFixture):
    """La date de clôture se trace à chaque passage en « faite », et
    s'efface si l'action se rouvre."""

    def test_passage_en_faite_date(self):
        self.action.statut = Action.Statut.FAITE
        self.action.save()
        self.action.refresh_from_db()
        self.assertIsNotNone(self.action.date_cloture)

    def test_reouverture_efface_puis_redate(self):
        self.action.statut = Action.Statut.FAITE
        self.action.save()
        self.action.statut = Action.Statut.A_FAIRE
        self.action.save()
        self.action.refresh_from_db()
        self.assertIsNone(self.action.date_cloture)
        self.action.statut = Action.Statut.FAITE
        self.action.save()
        self.action.refresh_from_db()
        self.assertIsNotNone(self.action.date_cloture)


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class AvertissementTests(PhotoFixture):
    """Règle des écrans n° 5 : clôturer sans photo « après » signale,
    sans jamais bloquer."""

    def donnees_modification(self, statut):
        return {
            "intitule": self.action.intitule,
            "description": self.action.description,
            "responsable": self.alice.id,
            "echeance": self.action.echeance.isoformat(),
            "statut": statut,
            "latitude": "",
            "longitude": "",
        }

    def test_cloturee_sans_photo_avertit(self):
        reponse = self.client.post(
            reverse("action_modifier", args=[self.action.pk]),
            self.donnees_modification(Action.Statut.FAITE),
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "sans photo")

    def test_cloturee_avec_photo_pas_avertissement(self):
        self.ajouter_photo_apres()
        reponse = self.client.post(
            reverse("action_modifier", args=[self.action.pk]),
            self.donnees_modification(Action.Statut.FAITE),
            follow=True,
        )
        self.assertContains(reponse, "Photo après")
        self.assertNotContains(reponse, "clôturée sans photo")


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class VueAvantApresTests(PhotoFixture):
    def test_sur_le_poste(self):
        self.ajouter_photo_avant()
        Action.objects.filter(pk=self.action.pk).update(
            statut=Action.Statut.FAITE
        )
        self.ajouter_photo_apres()
        reponse = self.client.get(
            reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertContains(reponse, "Avant / après")
        self.assertContains(reponse, "/medias/photos/")

    def test_sur_l_action(self):
        self.ajouter_photo_apres()
        reponse = self.client.get(
            reverse("action_detail", args=[self.action.pk])
        )
        self.assertContains(reponse, "/medias/photos/")

    def test_toutes_les_photos_dans_la_comparaison(self):
        """Plusieurs photos de chaque côté : la comparaison du poste
        les empile toutes, tuiles 4/3, sans démolir la mise en page."""
        self.ajouter_photo_avant()
        self.ajouter_photo_avant(taille=(900, 1600))
        Action.objects.filter(pk=self.action.pk).update(
            statut=Action.Statut.FAITE
        )
        self.ajouter_photo_apres()
        self.ajouter_photo_apres(taille=(900, 1600))
        reponse = self.client.get(
            reverse("poste_detail", args=[self.poste.pk])
        )
        self.assertContains(reponse, "Avant / après")
        self.assertContains(reponse, 'alt="Avant — ', count=2)
        self.assertContains(reponse, 'alt="Après — ', count=2)

    def test_action_faite_sans_photo_sollicitee(self):
        Action.objects.filter(pk=self.action.pk).update(
            statut=Action.Statut.FAITE
        )
        reponse = self.client.get(
            reverse("action_detail", args=[self.action.pk])
        )
        self.assertContains(reponse, "ajoute-la ici")


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class RevueAvantApresTests(PhotoFixture):
    def setUp(self):
        super().setUp()
        self.revue_precedente = Revue.objects.create(
            date=self.hier - timedelta(days=7)
        )
        self.revue = Revue.objects.create(date=self.hier)
        self.revue.postes.set([self.poste])
        self.ajouter_photo_avant()
        # .update() ne passe pas par save() : la date de clôture se
        # pose ici comme le ferait un vrai passage en « faite ».
        Action.objects.filter(pk=self.action.pk).update(
            statut=Action.Statut.FAITE,
            date_cloture=timezone.now() - timedelta(days=1),
        )
        self.ajouter_photo_apres()

    def test_cloturee_recemment_visible(self):
        reponse = self.client.get(
            reverse("revue_detail", args=[self.revue.pk])
        )
        self.assertContains(reponse, "Actions clôturées")
        self.assertContains(reponse, "Regler la hauteur")

    def test_toutes_les_photos_dans_la_comparaison(self):
        """Plusieurs photos de chaque côté : la revue les empile
        toutes, cadres pleins des deux côtés de la comparaison."""
        self.ajouter_photo_avant(taille=(1200, 1600))
        self.ajouter_photo_apres(taille=(1200, 1600))
        reponse = self.client.get(
            reverse("revue_detail", args=[self.revue.pk])
        )
        self.assertContains(reponse, 'alt="Avant — ', count=2)
        self.assertContains(reponse, 'alt="Après — ', count=2)

    def test_cloturee_avant_la_revue_precedente_absente(self):
        Action.objects.filter(pk=self.action.pk).update(
            date_cloture=timezone.now() - timedelta(days=30)
        )
        reponse = self.client.get(
            reverse("revue_detail", args=[self.revue.pk])
        )
        self.assertNotContains(reponse, "Actions clôturées")
