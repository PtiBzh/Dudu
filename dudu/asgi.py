"""Point d'entrée ASGI (non utilisé en v1, fourni par défaut)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dudu.settings")

application = get_asgi_application()
