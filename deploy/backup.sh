#!/usr/bin/env bash
# Respaldo diario de la base SQLite con retención de 14 días.
# Uso recomendado (cron del usuario que corre el servicio):
#   0 3 * * * /home/ubuntu/tablero_entrenador/deploy/backup.sh >> /var/log/tablero-backup.log 2>&1
set -euo pipefail

APP_DIR="/home/ubuntu/tablero_entrenador"
DB="${APP_DIR}/data/app.db"
UPLOADS="${APP_DIR}/data/uploads"
DEST="${APP_DIR}/backups"
RETENTION_DAYS=14

mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${DEST}/app-${STAMP}.db"

# .backup hace una copia consistente incluso con WAL activo y la app en marcha.
sqlite3 "$DB" ".backup '${OUT}'"
gzip -f "$OUT"

# Medios subidos (imágenes/gifs de ejercicios), si existen.
if [ -d "$UPLOADS" ]; then
  tar -czf "${DEST}/uploads-${STAMP}.tar.gz" -C "${APP_DIR}/data" uploads
fi

# Borra respaldos más antiguos que la retención.
find "$DEST" -name 'app-*.db.gz' -type f -mtime "+${RETENTION_DAYS}" -delete
find "$DEST" -name 'uploads-*.tar.gz' -type f -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date -Is)] backup OK -> ${OUT}.gz (+ uploads si aplica)"
