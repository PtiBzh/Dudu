"""
Configuration Django du projet Dudu.

Spécifications : « Spec Dudu.md » (fonctionnel) et « Spec technique.md ».
En production (M7) : conteneur unique, volume /data, réseau local du club
et WireGuard uniquement — aucune exposition publique.
"""
from pathlib import Path

# Chemins -----------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Sécurité ----------------------------------------------------------------

# Clé de développement. En production, elle est fournie par variable
# d'environnement (M7) et n'est jamais versionnée.
import os
SECRET_KEY = os.environ.get(
    "DUDU_SECRET_KEY",
    "django-insecure-cle-de-developpement-a-remplacer-en-production",
)

# False en production (M7) ; piloté par variable d'environnement.
DEBUG = os.environ.get("DUDU_DEBUG", "1") == "1"

# Hôtes autorisés : en production, le nom/IP local du club (réseau
# local + WireGuard, jamais d'exposition publique). CSV par variable
# d'environnement.
ALLOWED_HOSTS = [
    hote.strip()
    for hote in os.environ.get("DUDU_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if hote.strip()
]

# Formulaires POST depuis une origine explicite (ex. http://dudu.local)
# le cas échéant — même-origine, inutile le plus souvent.
CSRF_TRUSTED_ORIGINS = [
    origine.strip()
    for origine in os.environ.get("DUDU_ORIGINES_CSFR", "").split(",")
    if origine.strip()
]

# Applications ------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dudu.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "dudu.wsgi.application"

# Base de données ---------------------------------------------------------
# SQLite en mode WAL (spec technique), dans le volume /data en
# production : base + photos + plans d'un seul tenant (sauvegardes).

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.environ.get("DUDU_DATA", str(BASE_DIR))) / "db.sqlite3",
        "OPTIONS": {"init_command": "PRAGMA journal_mode=WAL;"},
    }
}

# Authentification --------------------------------------------------------
# Toute l'équipe est identifiée, pas d'anonymat (spec fonctionnelle).

AUTH_USER_MODEL = "core.Utilisateur"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalisation ----------------------------------------------------

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# Fichiers statiques ------------------------------------------------------
# WhiteNoise sert les fichiers statiques depuis l'application :
# c'est ce qui permet un conteneur unique, sans nginx.

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Divers ------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Photos (M5) ---------------------------------------------------------------
# Les photos compressées vivent sous /data en production (volume
# persistant : base + photos + plans d'un seul tenant pour les
# sauvegardes). En dev, le dossier data/ du projet suffit.

MEDIA_URL = "/medias/"
MEDIA_ROOT = Path(os.environ.get("DUDU_DATA", str(BASE_DIR / "data")))

# Carte (M3) ---------------------------------------------------------------
# Centre et zoom initiaux de la carte et des mini-cartes de saisie.
# Réglage d'affichage du club : remplacer par les coordonnées réelles du
# centre nautique (surcharge possible par variable d'environnement).

DUDU_CENTRE_CARTE = tuple(
    float(c)
    for c in os.environ.get("DUDU_CENTRE_CARTE", "48.42,-4.55").split(",")
)
DUDU_ZOOM_CARTE = int(os.environ.get("DUDU_ZOOM_CARTE", "16"))
