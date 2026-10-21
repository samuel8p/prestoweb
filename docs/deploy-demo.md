# Modo demo de Presto

Este documento describe cómo levantar Presto en **modo demo**: el stack completo
con el dinero **simulado** y los avisos de las notificaciones entrando **por
consola**, es decir **en los logs del worker**, sin depender de ningún servidor
de email.

> La fuente de verdad del proyecto es [AGENTS.md](../AGENTS.md). Este documento
> explica el modo demo y los pasos de despliegue; no reemplaza las reglas.

## 1. Qué es el modo demo

El modo demo se activa con la variable de entorno **`DEMO_MODE=true`**:

| Consecuencia | Detalle |
|---|---|
| Dinero simulado | `LEDGER_SIMULATED_DEPOSITS_ENABLED` queda en `True`: los depósitos y retiros de `ledger` funcionan sin proveedor de pagos |
| System check `ledger.E001` | En producción sigue bloqueando el dinero simulado, **excepto** en modo demo (ahí está habilitado a propósito) |
| Email | Sin `EMAIL_HOST`, el backend por defecto es el de **consola**: los avisos salen en los logs del worker |
| Cabecera | Todas las respuestas llevan `X-Presto-Mode: demo` |
| Metadata | `GET /api/v1/meta/` responde `{"mode": "demo", "simulated_money": true}` |

Sin `DEMO_MODE` (o con `DEMO_MODE=false`) la aplicación corre en modo
`production`: el dinero simulado queda bloqueado y `GET /api/v1/meta/` responde
`{"mode": "production", "simulated_money": false}`.

El stack de desarrollo (`docker-compose.yml`) ya viene con `DEMO_MODE=true`.

## 2. Cómo levantarlo en local

```sh
make up                                   # docker compose up --build -d
docker compose ps                         # db, redis, web, worker, beat
docker compose logs -f worker             # acá salen los emails de la demo
```

Para ver los avisos de las notificaciones:

```sh
docker compose logs -f worker | grep -A 10 "Subject:"
```

Y para saber en qué modo corre:

```sh
curl -s http://127.0.0.1:8000/api/v1/meta/
# {"mode": "demo", "simulated_money": true}
```

## 3. Cómo se ve un aviso en la consola

El backend de consola escribe el email completo (asunto, remitente,
destinatario y cuerpo) en la salida estándar del worker:

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

## 5. El email: consola o SMTP

| Configuración | Backend por defecto | Dónde se ven los avisos |
|---|---|---|
| Sin `EMAIL_HOST` (modo demo) | `django.core.mail.backends.console.EmailBackend` | en los **logs del worker** |
| Con `EMAIL_HOST` definido | `django.core.mail.backends.smtp.EmailBackend` | en la bandeja del destinatario |

Un `EMAIL_BACKEND` explícito **manda siempre**.

Para pasar a un SMTP de verdad:

```sh
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario-smtp
EMAIL_HOST_PASSWORD=clave-secreta
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@presto.example.com
```

Los secretos **no van en el repo**: `.env.prod.example` documenta todas las
variables y hay que copiarlo a `.env.prod` (que está en el `.gitignore`).

## 6. Despliegue en una plataforma con Docker Compose

El archivo es `docker-compose.prod.yml`. Los secretos llegan por variables de
entorno y el proxy inverso con TLS es **opcional**.

### 6.1 Preparar las variables

```sh
cp .env.prod.example .env.prod
$EDITOR .env.prod        # DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_ALLOWED_HOSTS, DOMAIN
```

### 6.2 Levantar

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

El `web` corre las migraciones y después `gunicorn` ✓. `worker` y `beat` usan la
misma imagen ✓.

### 6.3 Entrada pública: con proxy (Caddy) o sin proxy

**Con el proxy (perfil `proxy`)** — Caddy pide el certificado TLS solo para el
dominio de `DOMAIN` y es el **único** servicio que publica puertos 80/443; el
`web` queda solo en la red interna del compose:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile proxy up -d
```

Caddy reenvía las peticiones al `web` y pone `X-Forwarded-Proto: https`, que la
aplicación usa para no redirigir en loop ✓.

**Sin el proxy** — para cuando la plataforma ya da HTTPS (Railway, Render, Fly,
Coolify, un VPS con su propio Nginx). En ese caso la plataforma tiene que
llegar al contenedor del `web`; si su plataforma exige un puerto publicado, sumá
esto al servicio `web` del compose:

```yaml
    ports:
      - "127.0.0.1:8000:8000"
```

### 6.4 Backups diarios de PostgreSQL

El servicio `backup` (perfil `backup`) corre `deploy/backup-postgres.sh` una vez
por día: `pg_dump` comprimido con gzip y **rotación** (conserva los últimos
`BACKUP_KEEP`, 14 por defecto) en el volumen `backups`.

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile backup up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backup ls -la /backups
```

**Restaurar** (el procedimiento está también en el encabezado del script):

```sh
gunzip -c presto-AAAAMMDD-HHMMSS.sql.gz | psql -U presto -d presto
```

Para restaurarlo en otra base primero `createdb -U presto presto_restore` y
después `psql -U presto -d presto_restore` ✓. Conviene **probar la restauración**
de vez en cuando: un backup que nunca se restauró no es un backup.

### 6.5 Chequeos después de desplegar

```sh
curl -s http://127.0.0.1:8000/health/          # {"status": "ok"}
curl -s http://127.0.0.1:8000/api/v1/meta/     # {"mode": "production", "simulated_money": false}
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f worker
```

## 7. Compatibilidad arm64 (Oracle Cloud Ampere)

Las VM de Oracle Cloud en Linux son **aarch64** (ARM), no x86. Todo el stack se
verificó contra esa arquitectura el **2026-10-21**:

| Imagen | `linux/arm64` | `linux/amd64` |
|---|---|---|
| `python:3.12-slim` (base del `Dockerfile`) | ✅ | ✅ |
| `postgres:16` | ✅ | ✅ |
| `redis:7-alpine` | ✅ | ✅ |
| `caddy:2-alpine` (perfil `proxy`) | ✅ | ✅ |

Cómo se verificó:

```sh
docker buildx imagetools inspect python:3.12-slim     # y postgres:16, redis:7-alpine, caddy:2-alpine
docker buildx build --platform linux/arm64 --load -t presto:arm64-check .
docker run --rm presto:arm64-check uname -m           # aarch64
```

El build de la imagen completa **para arm64 funciona** ✓ y dentro de la imagen
importan sin problema `django`, `djangorestframework`, `drf_spectacular`,
`psycopg2`, `argon2`, `celery`, `gunicorn` y `django-cors-headers` ✓.

Las dos únicas dependencias con código nativo tienen ruedas para aarch64 ✓
(`psycopg2-binary` 18 ruedas aarch64 y `argon2-cffi-bindings` 16 ✓), así que
no hace falta compilar nada en la VM. El resto son paquetes puros de Python ✓.

En el `Dockerfile` no hay nada específico de x86 ✓ (no hay `apt` con paquetes
binarios, ni `COPY` de binarios, ni `--platform` fijo ✗). `deploy/backup-postgres.sh`
es un script de bash ✓ y el `Caddyfile` es texto ✓: los dos funcionan igual en
ARM.

> La VM arma `linux/arm64` de forma nativa ✓: el `docker compose up --build` de
> producción no necesita `--platform` ni QEMU ✗.

## 8. Caveats conocidos del modo demo

- **El KYC se resuelve desde el admin**: para crear ofertas, aceptar préstamos o
  abrir inversiones, el usuario tiene que tener el KYC aprobado. Se aprueba en
  `/admin/identity/kycverification/`.
- **Los productos de inversión los crea staff** desde el admin.
- Los datos viven en el volumen de PostgreSQL: `docker compose down -v` los
  borra.
- `beat` corre **una sola instancia**: escalar el worker está bien, el scheduler
  no.
- El `ledger` es **inmutable**: los movimientos no se editan, se revierten con
  un movimiento compensatorio (acción de admin, solo staff).

## 9. Comandos de verificación

```sh
docker compose run --rm web python -m pytest -q          # suite completa
docker compose run --rm web ruff check .                  # lint
docker compose run --rm web lint-imports                 # límites entre apps
docker compose run --rm web python manage.py check        # system checks
docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml
docker compose -f docker-compose.prod.yml config         # compose de producción
```
