from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Application unique de Dudu (voir Spec technique.md : pas d'éclatement
    en multiples apps ; les postes, actions et revues vivront ici)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Dudu"
