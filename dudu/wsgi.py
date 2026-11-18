"""Point d'entrée WSGI pour gunicorn (voir Spec technique.md)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dudu.settings")

application = get_wsgi_application()
