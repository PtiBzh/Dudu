"""Routage principal de Dudu."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views

admin.site.site_header = "Administration Dudu"
admin.site.site_title = "Dudu"
admin.site.index_title = "Suivi d'amélioration des conditions de travail"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("", include("core.urls")),
    path(
        "connexion/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
]

if settings.DEBUG:
    # Dev uniquement : en production WhiteNoise sert les statiques et
    # les médias restent dans le volume, servis par l'app (M7).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
