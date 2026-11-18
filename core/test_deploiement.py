"""Tests M7 : déploiement — les médias passent par une vue identifiée
(aucune exposition publique), la sauvegarde quotidienne copie la base
SQLite à chaud (`.backup`) et mirror les photos/plans vers
BACKUP_DEST, avec rétention et contrôle consigné au journal."""
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Utilisateur

MEDIAS_TESTS = tempfile.mkdtemp(prefix="dudu-deploiement-tests-")
SCRIPT_SAUVEGARDE = Path(settings.BASE_DIR) / "scripts" / "sauvegarde.sh"


@override_settings(MEDIA_ROOT=MEDIAS_TESTS)
class MediasTests(TestCase):
    """Depuis M7, /medias/ exige une session : les photos et plans du
    volume ne se servent pas publiquement (spec « aucune exposition
    publique »)."""

    def setUp(self):
        self.alice = Utilisateur.objects.create_user(
            "alice", password="mot de passe-123"
        )
        self.client.login(username="alice", password="mot de passe-123")
        default_storage.save("photos/essai.jpg", ContentFile(b"octets-de-photo"))

    def test_identifie_recupere_le_media(self):
        reponse = self.client.get(reverse("medias", args=["photos/essai.jpg"]))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            b"".join(reponse.streaming_content), b"octets-de-photo"
        )

    def test_anonyme_redirige(self):
        self.client.logout()
        reponse = self.client.get(reverse("medias", args=["photos/essai.jpg"]))
        self.assertEqual(reponse.status_code, 302)

    def test_evasion_de_chemin_refusee(self):
        for chemin in ("../spec.txt", "photos/../../requirements.txt"):
            reponse = self.client.get(reverse("medias", args=[chemin]))
            self.assertEqual(reponse.status_code, 404)

    def test_media_absent(self):
        reponse = self.client.get(
            reverse("medias", args=["photos/nulle-part.jpg"])
        )
        self.assertEqual(reponse.status_code, 404)


class BancSauvegarde:
    """Banc d'essai du script scripts/sauvegarde.sh : un /data en
    miniature (base SQLite réelle, photos, plans) et une destination
    jetable. Le script tourne tel quel, via sh — la CI le vérifie à
    chaque push, Docker n'a rien à voir."""

    def __init__(self):
        self.racine = Path(tempfile.mkdtemp(prefix="dudu-sauvegarde-tests-"))
        self.donnees = self.racine / "data"
        for dossier in ("photos", "plans", "sauvegardes"):
            (self.donnees / dossier).mkdir(parents=True)
        (self.donnees / "photos" / "photo.jpg").write_bytes(b"jpeg")
        (self.donnees / "plans" / "plan.png").write_bytes(b"png")
        with sqlite3.connect(self.donnees / "db.sqlite3") as base:
            base.execute("CREATE TABLE temoin (valeur TEXT)")
            base.execute("INSERT INTO temoin VALUES ('intacte')")
        self.destination = self.racine / "dest"

    def nettoyer(self):
        shutil.rmtree(self.racine, ignore_errors=True)

    def lancer(self, **reglages):
        environnement = {
            **os.environ,
            "DUDU_DATA": str(self.donnees),
            "BACKUP_DEST": str(self.destination),
            **reglages,
        }
        return subprocess.run(
            ["sh", str(SCRIPT_SAUVEGARDE)],
            env=environnement,
            capture_output=True,
            text=True,
            timeout=60,
        )

    @property
    def journal(self):
        chemin = self.donnees / "sauvegardes" / "journal.log"
        return chemin.read_text() if chemin.exists() else ""

    @property
    def base_sauvegardes(self):
        return self.donnees / "sauvegardes" / "base"


class SauvegardeTests(TestCase):
    """Spec : copie à chaud de SQLite, rsync photos/plans, rétention 90
    jours, contrôle (taille + nombre de fichiers) au journal."""

    def setUp(self):
        self.banc = BancSauvegarde()
        self.addCleanup(self.banc.nettoyer)

    def test_base_copiee_intacte(self):
        reponse = self.banc.lancer()
        self.assertEqual(reponse.returncode, 0, reponse.stderr)
        copies = list(self.banc.base_sauvegardes.glob("db-*.sqlite3"))
        self.assertEqual(len(copies), 1)
        with sqlite3.connect(copies[0]) as copie:
            valeur = copie.execute("SELECT valeur FROM temoin").fetchone()[0]
        self.assertEqual(valeur, "intacte")

    def test_rejouee_le_meme_jour_elle_ecrase(self):
        self.banc.lancer()
        self.banc.lancer()
        self.assertEqual(len(list(self.banc.base_sauvegardes.glob("db-*.sqlite3"))), 1)

    def test_miroir_photos_et_plans(self):
        reponse = self.banc.lancer()
        self.assertEqual(reponse.returncode, 0, reponse.stderr)
        self.assertTrue((self.banc.destination / "photos" / "photo.jpg").exists())
        self.assertTrue((self.banc.destination / "plans" / "plan.png").exists())
        # miroir : un plan supprimé au club disparaît de la copie
        (self.banc.donnees / "plans" / "plan.png").unlink()
        self.banc.lancer()
        self.assertFalse((self.banc.destination / "plans" / "plan.png").exists())

    def test_journal_consigne_le_controle(self):
        self.banc.lancer()
        self.assertIn("SAUVEGARDE OK", self.banc.journal)
        self.assertIn("fichiers=2", self.banc.journal)  # photo + plan
        self.assertIn("taille=", self.banc.journal)

    def test_sans_destination_annule(self):
        reponse = self.banc.lancer(BACKUP_DEST="")
        self.assertNotEqual(reponse.returncode, 0)
        self.assertIn("annulée", self.banc.journal)

    def test_retention_epure_les_vieilles_copies(self):
        self.banc.lancer()  # crée la copie du jour
        ancienne = self.banc.base_sauvegardes / "db-2000-01-01.sqlite3"
        ancienne.write_bytes(b"vieille")
        veille = time.time() - 91 * 86400
        os.utime(ancienne, (veille, veille))
        reponse = self.banc.lancer()
        self.assertEqual(reponse.returncode, 0, reponse.stderr)
        self.assertFalse(ancienne.exists())  # plus vieille que 90 jours
        self.assertEqual(
            len(list(self.banc.base_sauvegardes.glob("db-*.sqlite3"))), 1
        )  # celle du jour survit
