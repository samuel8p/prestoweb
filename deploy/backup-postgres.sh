#!/usr/bin/env bash
# Backup diario de PostgreSQL: pg_dump comprimido con rotación.
#
# Corre desde el servicio `backup` del compose de producción (perfil
# `backup`) o a mano:
#
#   ./deploy/backup-postgres.sh
#
# Variables de entorno:
#   PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD  (conexión)
#   BACKUP_DIR   dónde deja los archivos (por defecto ./backups)
#   BACKUP_KEEP  cuántos archivos conserva (por defecto 14)
#
# RESTAURAR (procedimiento):
#   1..copy el archivo .sql.gz a la máquina donde vive la base
#   2. gunzip -c presto-AAAAMMDD-HHMMSS.sql.gz | psql -U presto -d presto
#      (para restaurar en otra base: createdb -U presto presto_restore y
#      psql -U presto -d presto_restore)
#   3. verificá: psql -U presto -d presto -c 'select count(*) from ledger_ledgertransaction'
#   4. el dump es de tipo "plain" con --no-owner: las tablas y los datos se
#      restauran, pero los permisos (GRANT) no: revisalos si hacés falta.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
TIMESTAMP="$(date -u '+%Y%m%d-%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/presto-${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

TEMP_FILE="${BACKUP_FILE}.tmp"
echo "[backup] dumping ${PGDATABASE:-presto} to ${BACKUP_FILE}"
# Se vuelca a un archivo temporal: si el dump falla no queda un backup roto.
if ! pg_dump --no-owner --no-privileges --format=plain | gzip -9 > "${TEMP_FILE}"; then
  rm -f "${TEMP_FILE}"
  echo "[backup] falló el dump de ${PGDATABASE:-presto}" >&2
  exit 1
fi
mv "${TEMP_FILE}" "${BACKUP_FILE}"

# La rotación deja los BACKUP_KEEP archivos más nuevos.
ls -1t "${BACKUP_DIR}"/presto-*.sql.gz 2>/dev/null \
  | tail -n "+$((BACKUP_KEEP + 1))" \
  | xargs -r rm --

echo "[backup] listo: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"
echo "[backup] archivos conservados: $(ls -1 "${BACKUP_DIR}"/presto-*.sql.gz 2>/dev/null | wc -l)"
