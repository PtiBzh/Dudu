#!/bin/sh
# Dudu — sauvegarde quotidienne (M7).
#
# Ce que la spec demande, ce que fait ce script :
#   1. copie à chaud de SQLite (`.backup` de l'API sqlite3 : Reader ne
#      bloque pas les inscriptions pendant la copie),
#   2. rsync des photos et des plans vers BACKUP_DEST (miroir : ce qui
#      disparaît du club disparaît de la sauvegarde — et réciproquement
#      rien ne se perd),
#   3. rétention configurable (90 jours par défaut) sur les copies de
#      base ; les photos/plans, elles, ne disparaissent jamais de
#      l'app, donc rien à purger de leur côté,
#   4. contrôle simple consigné au journal : nombres de fichiers et
#      taille — l'anomalie sort avec un code non nul.
#
# Variables d'environnement : DUDU_DATA (défaut /data), BACKUP_DEST
# (obligatoire), DUDU_RETENTION_JOURS (défaut 90). En conteneur, le
# cron relit /data/sauvegardes/env (cron n'hérite pas de l'env) ; un
# appel manuel avec DUDU_DATA dans l'environnement ne lit PAS ce
# fichier (garde des tests).
set -u

if [ -z "${DUDU_DATA:-}" ] && [ -f /data/sauvegardes/env ]; then
  # cron n'hérite pas de l'environnement du conteneur
  . /data/sauvegardes/env
fi

: "${DUDU_DATA:=/data}"
: "${DUDU_RETENTION_JOURS:=90}"

mkdir -p "$DUDU_DATA/sauvegardes"
journal="$DUDU_DATA/sauvegardes/journal.log"
debut="$(date '+%F %T')"

if [ -z "${BACKUP_DEST:-}" ]; then
  echo "$debut CONTROLE BACKUP_DEST non renseigné — sauvegarde annulée." >> "$journal"
  exit 1
fi

if [ ! -f "$DUDU_DATA/db.sqlite3" ]; then
  echo "$debut CONTROLE base $DUDU_DATA/db.sqlite3 absente — sauvegarde annulée." >> "$journal"
  exit 1
fi

mkdir -p "$DUDU_DATA/sauvegardes/base" "$BACKUP_DEST"

# 1. Copie à chaud de la base ----------------------------------------
# horodatée au jour : rejouer le même jour écrase la copie du jour.
horodatage="$(date '+%F')"
copie="$DUDU_DATA/sauvegardes/base/db-$horodatage.sqlite3"
python3 - "$DUDU_DATA/db.sqlite3" "$copie" <<'PY'
import sqlite3
import sys

source, cible = sys.argv[1], sys.argv[2]
with sqlite3.connect(source) as base, sqlite3.connect(cible) as copie:
    base.backup(copie)
PY
base_ok=$?

# 2. Miroir des photos et plans --------------------------------------
rsync -a --delete "$DUDU_DATA/photos/" "$BACKUP_DEST/photos/"
photos_ok=$?
rsync -a --delete "$DUDU_DATA/plans/" "$BACKUP_DEST/plans/"
plans_ok=$?

# 3. Rétention des copies de base ------------------------------------
find "$DUDU_DATA/sauvegardes/base" -name 'db-*.sqlite3' -type f \
  -mtime +"$DUDU_RETENTION_JOURS" -delete

# 4. Contrôle simple : nombres et taille -----------------------------
compte_source=$(find "$DUDU_DATA/photos" "$DUDU_DATA/plans" -type f 2>/dev/null | wc -l | tr -d ' ')
compte_copie=$(find "$BACKUP_DEST/photos" "$BACKUP_DEST/plans" -type f 2>/dev/null | wc -l | tr -d ' ')
taille=$(du -sb "$BACKUP_DEST" 2>/dev/null | cut -f1)
taille=${taille:-0}

if [ "$base_ok" -ne 0 ] || [ "$photos_ok" -ne 0 ] || [ "$plans_ok" -ne 0 ] \
  || [ "$compte_source" -ne "$compte_copie" ]; then
  echo "$debut ANOMALIE base=$base_ok photos=$photos_ok plans=$plans_ok \
fichiers=$compte_copie attendus=$compte_source taille=$taille" >> "$journal"
  exit 1
fi

echo "$debut SAUVEGARDE OK base=db-$horodatage.sqlite3 \
fichiers=$compte_source taille=$taille" >> "$journal"
