# Modo demo de Presto

Este documento describe cómo levantar Presto en **modo demo**: el stack local
completo, con los avisos de las notificaciones entrando **por consola**, es decir
**en los logs del worker**, sin depender de ningún servidor de email.

> La fuente de verdad del proyecto es [AGENTS.md](../AGENTS.md). Este documento
> solo explica el modo demo y sus diferencias con un despliegue real.

## 1. Qué es el modo demo

Es el stack de `docker-compose.yml` (desarrollo): PostgreSQL, Redis, Django,
el worker de Celery y el beat. La diferencia con producción es que **el email
sale por consola**:

| Configuración | Backend por defecto | Dónde se ven los avisos |
|---|---|---|
| Sin `EMAIL_HOST` (modo demo) | `django.core.mail.backends.console.EmailBackend` | en los **logs del worker** |
| Con `EMAIL_HOST` definido | `django.core.mail.backends.smtp.EmailBackend` | en la bandeja del destinatario |

Un `EMAIL_BACKEND` explícito **manda siempre**: si lo definís, se respeta y no
se aplica la regla de arriba.

## 2. Cómo levantarlo

```sh
make up                                   # docker compose up --build -d
docker compose ps                         # db, redis, web, worker, beat
docker compose logs -f worker             # acá salen los emails de la demo
```

Para ver los avisos de las notificaciones:

```sh
docker compose logs -f worker | grep -A 10 "Subject:"
```

## 3. Cómo se ve un aviso en la consola

El backend de consola escribe el email completo (asunto, remitente,
destinatario y cuerpo) en la salida estándar del worker, algo como:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Subject: Presto: tenés una cuota por vencer
From: no-reply@presto.local
To: destinatario@example.com

Hola,

La cuota 1 de tu préstamo vence el 2026-11-21.
El importe de la cuota es 1040.26 ARS.

Podés ver el detalle de tu préstamo desde Presto.
```

## 4. Los cuatro avisos que puede generar la demo

| Evento | Cuándo se dispara | Quién lo recibe |
|---|---|---|
| `installment_due_soon` | tarea diaria del beat a las **00:10 UTC** (cuota que vence en ≤3 días) | el prestatario |
| `installment_overdue` | tarea diaria del beat a las **00:20 UTC** (cuota vencida) | el prestatario y el prestamista |
| `investment_settled` | al liquidarse una posición de inversión | el inversionista |
| `budget_alert` | al categorizar un movimiento que cruza el umbral del presupuesto | el usuario |

El usuario puede desactivar cada tipo de aviso desde
`PUT /api/v1/notifications/preferences/` (los desactivados no generan ni aviso
ni email).

## 5. Cómo pasar a un SMTP de verdad

Definí en el entorno (o en un `.env.prod`):

```sh
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario-smtp
EMAIL_HOST_PASSWORD=clave-secreta
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@presto.example.com
```

Con `EMAIL_HOST` definido, el backend por defecto pasa a ser SMTP. Si además
querés fijar el backend explícitamente, usá `EMAIL_BACKEND`.

Los secretos **no van en el repo**: `.env.prod.example` documenta todas las
variables y hay que copiarlo a `.env.prod` (que está en el `.gitignore`).

## 6. Caveats conocidos del modo demo

- **Los depósitos y los retiros simulados están apagados** en el entorno local:
  `docker-compose.yml` no define `LEDGER_SIMULATED_DEPOSITS_ENABLED` y el valor
  por defecto de los settings es `False`. Para poder mover plata en la demo hay
  que exportarlo:

  ```sh
  LEDGER_SIMULATED_DEPOSITS_ENABLED=True docker compose up -d
  ```

  (en producción el system check `ledger.E001` impide que se activen).
- **El KYC se resuelve desde el admin**: para crear ofertas, aceptar préstamos o
  abrir inversiones, el usuario tiene que tener el KYC aprobado. Se aprueba en
  `/admin/identity/kycverification/`.
- **Los productos de inversión los crea staff** desde el admin.
- Los datos viven en el volumen de PostgreSQL: `docker compose down -v` los
  borra.
- `beat` corre **una sola instancia**: escalar el worker está bien, el scheduler
  no.

## 7. Comandos de verificación

```sh
docker compose run --rm web python -m pytest -q          # suite completa
docker compose run --rm web ruff check .                  # lint
docker compose run --rm web lint-imports                 # límites entre apps
docker compose run --rm web python manage.py check        # system checks
docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml
```
