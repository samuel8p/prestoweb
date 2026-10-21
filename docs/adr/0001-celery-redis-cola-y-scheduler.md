# ADR 0001 — Celery + Redis como cola de tareas y scheduler

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** infraestructura transversal (Bloque 6 del plan de Presto)

## Contexto

`AGENTS.md` §3 elige Celery + Redis para las tareas asíncronas y §4 exige que
`config/celery.py` exista y que `docker compose up` levante el worker. §14 pide
que el entorno de desarrollo levante Django, PostgreSQL, Redis **y el worker de
Celery**. Hasta ahora el repositorio tenía `celery` declarado como dependencia
pero ningún archivo de Celery: las dos tareas periódicas del negocio
(`mark_overdue_loans` y `settle_investments`) eran management commands que
alguien tenía que acordarse de correr a mano.

El Bloque 6 (`budgets`, `reports`, `notifications`) necesita esa infraestructura
antes de poder enviar emails y recalcular presupuestos en background.

Restricciones que condicionan la decisión:

- AGENTS §2: monolito modular, **prohibido** introducir brokers de mensajes
  (RabbitMQ, Kafka) o bases de datos adicionales.
- AGENTS §3: no agregar dependencias sin justificarlas y pedir confirmación.
- AGENTS §4: cada app de dominio tiene un `tasks.py` ("Tareas Celery (si aplica)").
- AGENTS §5.2: una app solo puede usar a otra por `services.py`/`selectors.py`;
  `core` no puede importar ninguna otra app.
- AGENTS §5.3: los receptores de señales deben ser idempotentes y delegar el
  trabajo pesado a tareas Celery.
- AGENTS §12: las migraciones se revisan antes de aplicarse → se prefiere no
  agregar tablas.

## Decisión

1. **Celery 5.6 con Redis como broker**, con `config/celery.py` como punto único
   de configuración. Redis ya existía como servicio del `docker-compose.yml`; no
   se agregó ninguna dependencia nueva (`celery` y `redis` ya estaban en
   `pyproject.toml`).
2. **Sin result backend persistente.** Las tareas del proyecto no devuelven
   resultados: producen efectos (marcar cuotas, liquidar posiciones). Se fija
   `CELERY_TASK_IGNORE_RESULT = True` y `CELERY_RESULT_BACKEND = None`, así que
   no se guarda nada y no hace falta `django-celery-results`.
3. **Las tareas viven en la app dueña**: `apps/loans/tasks.py` y
   `apps/investments/tasks.py`. No hay un `tasks.py` central en `core` porque
   `core` no puede importar `loans` ni `investments` (contrato `core-isolation`).
4. **Una sola capa de lógica de negocio**: la task y el management command
   llaman al mismo `services`. La task es un adaptador delgado, sin reglas de
   negocio propias; los management commands no se modifican y siguen siendo la
   vía manual y de recuperación.
5. **Nombres de task estables y explícitos**:
   `apps.loans.tasks.mark_overdue_loans` y
   `apps.investments.tasks.settle_investments`. El beat schedule los referencia
   por nombre, así que `config/celery.py` no importa ninguna app de dominio.
6. **Beat diario en UTC**: `mark_overdue_loans` a las 00:05 y
   `settle_investments` a las 00:15. `TIME_ZONE` del proyecto es UTC.
7. **Scheduler con volumen persistente**: el archivo de estado de
   `celery.beat.PersistentScheduler` vive en un volumen Docker
   (`celerybeat:/var/celerybeat`), no en el working tree. No se agregó
   `django-celery-beat` justamente para no sumar dependencias.
8. **Los tests no dependen de Redis**: `CELERY_TASK_ALWAYS_EAGER = True` en
   `config/settings/test.py`. La suite sigue corriendo contra PostgreSQL real.
9. **Fallar rápido en producción**: `config/settings/production.py` exige
   `CELERY_BROKER_URL` o `REDIS_URL`; sin broker el worker no arranca.

## Consecuencias

**Positivas**

- Las tareas periódicas dejan de depender de que alguien se acuerde de correrlas.
- La app `notifications` (Bloque 6) ya tiene cola, worker y scheduler.
- Los management commands quedan como herramienta manual y de recuperación, sin
  duplicar reglas de negocio.
- Cero dependencias nuevas y cero migraciones.

**Negativas / riesgos asumidos**

- Hay que operar **una sola** instancia de `beat`: dos schedulers dispatcharían
  la misma tarea dos veces. El diseño es idempotente por service, pero en
  producción hay que garantizar una sola réplica (pendiente del `Fase 7`).
- `celery beat` guarda su estado en un archivo: si se pierde el volumen, el
  scheduler recalcula las próximas ejecuciones. Aceptable para tareas diarias.
- Celery no es una dependencia de Django: `celery -A config` requiere
  `DJANGO_SETTINGS_MODULE` en el entorno.
- `config/__init__.py` importa la app de Celery, así que cualquier proceso que
  importe `config` (incluido `manage.py`) carga Celery. Es el patrón oficial de
  Django + Celery y el costo es despreciable.
- La configuración vive en dos lugares: `CELERY_*` en los settings (broker,
  serialización, límites) y el `beat_schedule` en `config/celery.py`.

**Pendiente**

- `docker-compose.prod.yml` y el despliegue real (Fase 7) tienen que definir
  cómo corre el worker y garantizar una sola instancia de `beat`.
- El envío de emails (`notifications`) definirá el backend de email y los
  templates; esa parte no se decidió acá.
