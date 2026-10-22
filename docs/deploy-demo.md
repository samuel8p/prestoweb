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

### 6.6 Recursos: workers del web y del worker

Las dos concurrencias se ajustan **por entorno**, sin tocar el compose:

| Variable | Qué controla | Default |
|---|---|---|
| `GUNICORN_WORKERS` | procesos de gunicorn (el web) | 3 |
| `CELERY_WORKER_CONCURRENCY` | procesos del worker de Celery | 2 |

Valores recomendados según la RAM de la VM (el `beat` corre **una sola**
instancia, no se escala):

| VM | RAM | `GUNICORN_WORKERS` | `CELERY_WORKER_CONCURRENCY` |
|---|---|---|---|
| 1 OCPU | 6 GB | **2** | **2** |
| 2 OCPU | 12 GB | **4** | **4** |

Los procesos de gunicorn son los que más RAM consumen (cada uno es un proceso
de Django con su copia de la aplicación); los del worker de Celery son tareas
de E/S (emails y avisos) y aguantan más concurrencia sin memoria.

> No hay límites de memoria configurados a propósito: los límites duros
> (`mem_limit`, `deploy.resources`) matan el proceso cuando se pasan, y en una VM
> de 6 GB es preferible que el sistema avise antes de que el OOM killer mate un
> proceso a mitad de una operación de dinero.

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

## 8. Oracle Cloud (Ubuntu 24.04 ARM) + DuckDNS + Vercel

Despliegue completo en una VM de Oracle Cloud con Ubuntu 24.04 **aarch64**, un
subdominio de DuckDNS y el front en Vercel. Todo lo de este capítulo está
verificado contra el stack de producción (ver §7 para la compatibilidad ARM).

> La VM tiene que ser **ARM (Ampere A1)**: el stack es multi-arch ✓ y funciona
> igual en x86 ✗ (no hace falta nada especial en ninguno de los dos casos ✓).

### 8.1 Preparar la VM

```sh
# 1. Sistema actualizado
sudo apt update && sudo apt -y upgrade

# 2. Docker y el plugin de Compose (la forma oficial para Ubuntu)
sudo apt -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# 3. El usuario del servicio en el grupo de Docker (si no, tenés que usar sudo)
sudo usermod -aG docker $USER && newgrp docker
docker version && docker compose version
```

> Con la VM de 1 GB de RAM, agregá **swap** (si no, el build de la imagen se
> queda sin memoria):
>
> ```sh
> sudo fallocate -l 2G /swapfile
> sudo chmod 600 /swapfile
> sudo mkswap /swapfile
> sudo swapon /swapfile
> echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
> ```
>
> Con 6 GB o 12 GB el swap no hace falta ✗.

### 8.2 Firewall: abrir 80 y 443 en la VM

Las imágenes de Ubuntu de Oracle Cloud traen **reglas de iptables que bloquean
el tráfico de entrada**, aunque la *Security List* de la VCN esté abierta. Por eso el
puerto 80/443 hay que abrirlo **dentro de la VM** además de en el panel:

```sh
# Ver las reglas actuales
sudo iptables -L INPUT -n -v --line-numbers

# Abrir 80 y 443 (y 22, que suele estar permitido)
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Persistir las reglas (sin esto, se pierden al reiniciar)
sudo apt -y install iptables-persistent
sudo netfilter-persistent save
```

En una VM de 1 GB, además, hay que levantar los límites de conexiones:

```sh
sudo sysctl -w net.netfilter.nf_conntrack_max=65536
echo 'net.netfilter.nf_conntrack_max=65536' | sudo tee -a /etc/sysctl.conf
```

En el **panel de Oracle** además hay que confirmar la *Security List* de la VCN
con los puertos **TCP 80 y 443** (y **22** para el SSH) ✓.

### 8.3 DuckDNS: el subdominio

1. Creá una cuenta en [duckdns.org](https://www.duckdns.org) y anotá el token.
2. Apuntá el subdominio a la IP pública de la VM:

```sh
curl -s "https://www.duckdns.org/update?domains=presto-demo&token=TOKEN&ip=IP_PUBLICA"
```

3. Actualizá el DNS desde la VM (o desde el cron del cliente) cada vez que
   cambie la IP. Es lo más simple dejar que DuckDNS apunte a la IP y, si la
   cambia, volver a correr el `curl` ✗ (si la IP es estática ✗ → una sola vez ✓).

El valor de `DOMAIN` en el `.env.prod` es **el subdominio completo** (sin
`https://` ni puerto), que es lo que Caddy usa para pedir el certificado TLS:

```sh
DOMAIN=presto-demo.duckdns.org
```

Con el perfil `proxy` Caddy pide el certificado Let's Encrypt de ese dominio y
es el único servicio que publica 80/443 ✓.

### 8.4 Clonar y configurar

```sh
git clone https://github.com/samuel8p/prestoweb.git
cd prestoweb

cp .env.prod.example .env.prod
nano .env.prod
```

Lo mínimo que hay que completar:

```sh
DJANGO_SECRET_KEY=<una clave de 50 caracteres o más: openssl rand -base64 48>
DJANGO_ALLOWED_HOSTS=presto-demo.duckdns.org
POSTGRES_PASSWORD=<una contraseña fuerte>
DOMAIN=presto-demo.duckdns.org
# Modo demo: dinero simulado y avisos por consola
DEMO_MODE=true
LEDGER_SIMULATED_DEPOSITS_ENABLED=true
# CORS: el front en Vercel (separados por comas si hay más de uno)
CORS_ALLOWED_ORIGINS=https://presto-front.vercel.app
# Recursos (6 GB -> 2 y 2; 12 GB -> 4 y 4)
GUNICORN_WORKERS=2
CELERY_WORKER_CONCURRENCY=2
```

> `DJANGO_SECRET_KEY` se genera una vez y **no se cambia** después: cambiarla
> invalida los tokens JWT y la blacklist. Para rotarla:
> `openssl rand -base64 48` y se reinicia el stack ✓.

### 8.5 Levantar

```sh
# Con el proxy (Caddy + TLS) y los backups diarios
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  --profile proxy --profile backup up -d --build

docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

El servicio `web` aplica las migraciones solo al arrancar ✓.

### 8.6 Superusuario y datos de prueba

```sh
# Superusuario para el admin (/admin/)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec web python manage.py createsuperuser

# Los management commands que existen (no hay comando de seed: el KYC y los
# productos de inversión los carga staff desde el admin)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec web python manage.py mark_overdue_loans
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec web python manage.py settle_investments
```

Para tener **datos de prueba** en la demo hay que Approbar el KYC de un usuario
y crear un producto de inversión: los dos se hacen desde el admin (el KYC en
`/admin/identity/kycverification/` y los productos en
`/admin/investments/investmentproduct/`) ✗ porque ambos están restringidos a
**staff** por diseño ✓ (§7 del modo demo).

Alternativa, desde el shell de Django (para una demo de punta a punta):

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec web python manage.py shell -c "
import uuid
from decimal import Decimal
from apps.identity.services import register_user, submit_kyc, resolve_kyc
from apps.investments.models import InvestmentProduct
user = register_user(email='demo@presto.local', password='PrestoTest123!')
v = submit_kyc(user=user, documents={})
resolve_kyc(verification_id=v.id, status='approved', resolved_by_user_id=uuid.uuid4())
InvestmentProduct.objects.get_or_create(
    type='fixed_term', currency='ARS', term_days=30,
    defaults={'annual_rate_tna': Decimal('12.00'), 'min_amount': Decimal('1000.00'), 'status': 'active'})
print('demo lista')"
```

### 8.7 Verificar

```sh
# 1. El servicio responde (desde la VM, por el proxy)
curl -s https://presto-demo.duckdns.org/health/
# {"status": "ok"}

curl -s https://presto-demo.duckdns.org/api/v1/meta/
# {"mode":"demo","simulated_money":true}

# 2. Un depósito simulado (con el token de un usuario con KYC aprobado)
curl -s -X POST https://presto-demo.duckdns.org/api/v1/ledger/transactions/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: primer-deposito" \
  -H "Content-Type: application/json" \
  -d '{"type":"deposit","currency":"ARS","amount":"1000.00"}'

# 3. El preflight CORS desde el origen del front
curl -i -X OPTIONS https://presto-demo.duckdns.org/api/v1/ledger/transactions/ \
  -H "Origin: https://presto-front.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" | head -20
# access-control-allow-origin: https://presto-front.vercel.app
```

Si el preflight no devuelve el header, revisá `CORS_ALLOWED_ORIGINS` en el
`.env.prod` (tiene que ser **exactamente** la URL del front ✓) y que el
servidor de la VM haya leído el archivo:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec web \
  python -c "from django.conf import settings; print(settings.CORS_ALLOWED_ORIGINS)"
```

### 8.8 Actualizar la aplicación

```sh
cd prestoweb
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  --profile proxy --profile backup up -d --build
```

El `up -d --build` recrea lo que cambió ✓ y el `web` aplica las migraciones
pendientes al arrancar ✓. Para ver qué pasó:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f web
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f worker
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f caddy
```

En el modo demo los avisos de las notificaciones salen en los logs del
`worker` ✓:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f worker | grep -A 10 "Subject:"
```

### 8.9 Backups y restauración

El servicio `backup` (perfil `backup`) hace un `pg_dump` comprimido por día y
conserva los últimos `BACKUP_KEEP` (14 por defecto ✓):

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backup ls -la /backups
```

Para **restaurar** un backup (pará la app antes ✗ → el ledger es inmutable y
una restauración con la app corriendo puede dejar movimientos a medias ✗):

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod stop web worker beat

docker compose -f docker-compose.prod.yml --env-file .env.prod exec backup \
  bash -c "gunzip -c /backups/presto-AAAAMMDD-HHMMSS.sql.gz | psql -U presto -d presto"

docker compose -f docker-compose.prod.yml --env-file .env.prod start web worker beat
```

Y una comprobación rápida de que la base quedó entera:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod exec db \
  psql -U presto -d presto -c 'select count(*) from ledger_ledgertransaction'
```

> El dump es de tipo *plain* con `--no-owner` ✓: se restauran las tablas y los
> datos ✓, pero no los permisos (`GRANT`) ✗ → revisalos si hacés falta ✓.

## 9. Caveats conocidos del modo demo

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

## 10. Comandos de verificación

```sh
docker compose run --rm web python -m pytest -q          # suite completa
docker compose run --rm web ruff check .                  # lint
docker compose run --rm web lint-imports                 # límites entre apps
docker compose run --rm web python manage.py check        # system checks
docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml
docker compose -f docker-compose.prod.yml config         # compose de producción
```
