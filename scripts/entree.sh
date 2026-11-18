#!/bin/sh
# Dudu — entrée du conteneur (M7) : migrations automatiques à chaque
# démarrage (« volume /data jamais écrasé, migrations Django
# automatiques », spec technique), cron de sauvegarde, puis gunicorn
# en premier plan.
set -e
cd /app

DATA="${DUDU_DATA:-/data}"
mkdir -p "$DATA/sauvegardes"

python manage.py migrate --no-input

# Cron de sauvegarde : BACKUP_DEST absent → pas de sauvegarde (on le
# dit dans le journal plutôt que de faire boucler le conteneur).
CRON="${DUDU_CRON:-30 3 * * *}"
if [ "$CRON" != "aucun" ]; then
  if [ -z "${BACKUP_DEST:-}" ]; then
    {
      date "+%F %T CONTROLE BACKUP_DEST non renseigné : sauvegarde quotidienne désactivée."
    } >> "$DATA/sauvegardes/journal.log"
  else
    # cron n'hérite pas de l'environnement du conteneur : on met à plat
    # les réglages dans un fichier que le script relit (chmod 600, il
    # porte le chemin de sauvegarde mais aucune donnée sensible).
    umask 177
    {
      echo "DUDU_DATA=$DATA"
      echo "BACKUP_DEST=$BACKUP_DEST"
      echo "DUDU_RETENTION_JOURS=${DUDU_RETENTION_JOURS:-90}"
    } > "$DATA/sauvegardes/env"
    printf '%s root sh /app/scripts/sauvegarde.sh >> %s/sauvegardes/journal.log 2>&1\n' \
      "$CRON" "$DATA" > /etc/cron.d/dudu-sauvegarde
    chmod 0644 /etc/cron.d/dudu-sauvegarde
    cron
  fi
fi

exec gunicorn dudu.wsgi:application \
  --bind "0.0.0.0:${DUDU_PORT:-8000}" \
  --workers "${DUDU_TRAVAILLEURS:-3}"
