# Dudu — conteneur unique (M7) : gunicorn + WhiteNoise + Pillow, cron
# de sauvegarde embarqué. Voir Spec technique.md (« Sécurité et
# déploiement ») : réseau local du club + WireGuard, aucune exposition
# publique, volume /data persistant.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DUDU_DEBUG=0 \
    DUDU_DATA=/data

# cron : la sauvegarde quotidienne tourne dans le conteneur ;
# rsync : c'est lui qui porte photos et plans vers BACKUP_DEST.
RUN apt-get update \
 && apt-get install -y --no-install-recommends cron rsync \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Les dépendances d'abord : cette couche ne change qu'à chaque
# évolution de requirements.txt, le reste du dépôt varie plus vite.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# WhiteNoise sert les statiques depuis l'image : on les collecte une
# fois, compressées, à la construction.
RUN python manage.py collectstatic --no-input

VOLUME /data
EXPOSE 8000

ENTRYPOINT ["sh", "/app/scripts/entree.sh"]
