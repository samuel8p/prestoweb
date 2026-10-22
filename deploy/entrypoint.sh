#!/usr/bin/env sh
# Entrypoint de la imagen de Presto.
#
# La **misma imagen** sirve para los dos roles del despliegue:
#
#   worker   -> celery (el worker de la cola, con o sin beat embebido)
#
# Cualquier otro comando se ejecuta tal cual (`entrypoint.sh <comando> ...`).
#
# Variables que lee:
#   CELERY_WORKER_CONCURRENCY procesos del worker de Celery (default 2)
#   CELERY_EMBED_BEAT         con "true" el worker arranca con el beat
#                             embebido (-B). OJO: con el beat embebido el
#                             worker tiene que correr en UNA sola réplica
#                             (el scheduler no se puede duplicar: el
#                             proyecto ya avisa de esto en el modo demo).

set -eu

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${APP_DIR}"

role="${1:-worker}"
[ "$#" -gt 0 ] && shift

case "${role}" in
  worker)
    beat_option=""
    if [ "${CELERY_EMBED_BEAT:-false}" = "true" ]; then
      beat_option="-B"
      echo "entrypoint: beat embebido (una sola réplica del worker)"
    fi
    # shellcheck disable=SC2086
    exec celery -A config worker -l info \
      --concurrency "${CELERY_WORKER_CONCURRENCY:-2}" \
      ${beat_option} \
      "$@"
    ;;
  *)
    exec "${role}" "$@"
    ;;
esac
