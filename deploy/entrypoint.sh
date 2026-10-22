#!/usr/bin/env sh
# Entrypoint de la imagen de Presto.
#
# La **misma imagen** sirve para los dos roles del despliegue:
#
#   web      -> gunicorn (el servidor HTTP)
#   worker   -> celery (el worker de la cola, con o sin beat embebido)
#
# Cualquier otro comando se ejecuta tal cual (`entrypoint.sh <comando> ...`).
#
# Variables que lee:
#   PORT                      puerto del web (default 8000)
#   GUNICORN_WORKERS          procesos de gunicorn (default 3)
#   CELERY_WORKER_CONCURRENCY procesos del worker de Celery (default 2)
#   CELERY_EMBED_BEAT         con "true" el worker arranca con el beat
#                             embebido (-B). OJO: con el beat embebido el
#                             worker tiene que correr en UNA sola réplica
#                             (el scheduler no se puede duplicar: el
#                             proyecto ya avisa de esto en el modo demo).
#   RUN_MIGRATIONS            con "true" aplica las migraciones antes de
#                             arrancar. SOLO en el servicio web y con UNA
#                             sola réplica: si dos réplicas las aplican a la
#                             vez pueden chocar (una gana y la otra falla
#                             con el lock de la migración) y, peor, una
#                             puede empezar a atender tráfico con el
#                             schema a medio cambiar.

set -eu

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${APP_DIR}"

role="${1:-web}"
[ "$#" -gt 0 ] && shift

case "${role}" in
  web)
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
      echo "entrypoint: aplicando migraciones (RUN_MIGRATIONS=true)"
      python manage.py migrate --noinput
    fi
    exec gunicorn config.wsgi:application \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${GUNICORN_WORKERS:-3}" \
      "$@"
    ;;
  worker)
    beat_option=""
    schedule_option=""
    if [ "${CELERY_EMBED_BEAT:-false}" = "true" ]; then
      beat_option="-B"
      # El archivo del scheduler se escribe en el directorio que le
      # pertenece al usuario del contenedor (en /app no se puede: es del
      # usuario root).
      schedule_option="--schedule /var/celerybeat/celerybeat-schedule"
      echo "entrypoint: beat embebido (una sola réplica del worker)"
    fi
    # shellcheck disable=SC2086
    exec celery -A config worker -l info \
      --concurrency "${CELERY_WORKER_CONCURRENCY:-2}" \
      ${beat_option} \
      ${schedule_option} \
      "$@"
    ;;
  *)
    exec "${role}" "$@"
    ;;
esac
