# Despliegue en Northflank (plan gratuito) + Vercel

Guía de despliegue de Presto en **Northflank** con el plan gratuito (2 servicios,
2 bases administradas y 2 cron jobs) y el front en **Vercel**.

> La fuente de verdad del proyecto es [AGENTS.md](../AGENTS.md). Esta guía
> describe **el despliegue**; no cambia las reglas.
>
> No hay acceso a la interfaz de Northflank desde este repositorio: todo lo que
> no se puede comprobar desde acá está marcado como **"verificar en la UI"**.

## 1. El mapa del despliegue

| Recurso | Qué es | Imagen / plan |
|---|---|---|
| Servicio **web** | Django + gunicorn (la API y el admin) | La imagen del repo, comando `web` |
| Servicio **worker** | Celery **con el beat embebido** | La misma imagen, comando `worker`, **1 réplica** |
| Base 1 | **PostgreSQL administrada** | Add-on de Northflank |
| Base 2 | **Redis administrada** (broker de Celery) | Add-on de Northflank |
| Cron job 1 | `mark_overdue_loans` | Imagen del repo, comando de management |
| Cron job 2 | `settle_investments` | Imagen del repo, comando de management |
| Front | La interfaz en Vercel | Otro repositorio |

La **misma imagen** sirve para los dos servicios: lo único que cambia es el
comando (`web` o `worker`) y las variables de entorno.

**Sobre los cron jobs:** el worker ya lleva el beat embebido, así que las
tareas diarias (`mark_overdue_loans`, `notify_installments_due_soon`,
`notify_overdue_installments`, `settle_investments`) se disparan solas. Los dos
cron jobs del plan gratuito quedan para correr a mano lo que haga falta (por
ejemplo, liquidar inversiones al momento) y **no** deben apuntar a las mismas
tareas del schedule, o se van a duplicar ⚠️.

## 2. Antes de empezar

- El repositorio del backend tiene que estar en GitHub y **el build tiene que
  poder correr en la plataforma** (el `Dockerfile` del repo ✓).
- Una clave secreta: `openssl rand -base64 48` (o `python -c "import secrets;
  print(secrets.token_urlsafe(50))"`).
- La URL pública del front en Vercel (para el CORS).

## 3. Crear el proyecto y conectar GitHub

1. Crear el proyecto en Northflank (**verificar en la UI**: el nombre exacto
   de la opción y si hace falta elegir la región antes de crear los recursos).
2. **Elegir UNA sola región** y usarla para los cuatro recursos (proyecto, las
   dos bases y los dos cron jobs): la base administrada tiene que estar en la
   misma región que el servicio para que la conexión sea local y rápida
   (**verificar en la UI**: qué regiones hay disponibles y si los add-ons
  Strange usan la del proyecto por defecto).
3. Conectar el repositorio de GitHub:
   - **verificar en la UI**: si Northflank pide una app de GitHub o una clave
     SSH, y dónde se configura la carpeta y el branch (por defecto `main` ✓).
   - **Dar acceso solo al repositorio del backend**: si la UI pide elegir
     repositorios, marcar **solo** el del backend ✓ (el front es otro
     repositorio y no tiene por qué ver estas claves ⚠️).

## 4. Las bases administradas

### PostgreSQL

1. Crear el add-on de PostgreSQL en la región del proyecto (**verificar en la
   UI**: el nombre del add-on y si hay que elegir la versión ✓ → la app pide
   PostgreSQL 16 ✓).
2. Copiar la **cadena de conexión**: tiene que tener esta forma

   ```
   postgresql://USUARIO:CLAVE@HOST:PUERTO/presto
   ```

   Si la clave trae `@`, `:` o `/`, la plataforma la da percent-encoded ✓ y la
   aplicación la des-codifica ✓ (probado con tests ✓).
3. La base administrada suele pedir TLS: definí `DB_SSLMODE=require` ✓ (sin
   esa variable la conexión **no** pide SSL ✗).

### Redis

1. Crear el add-on de Redis (**verificar en la UI**: el nombre y si la URL
   viene con contraseña ✓).
2. Copiar la URL del broker:

   ```
   redis://:CLAVE@HOST:PUERTO
   ```

   La aplicación la normaliza (puerto y base por defecto ✓).

> Las dos cadenas de conexión son **secretos**: van en las variables de
> entorno del servicio, no en el repositorio ✓.

## 5. El servicio web

| Campo | Valor |
|---|---|
| Imagen | La del repositorio (el `Dockerfile` de la raíz ✓) |
| Comando | `web` |
| Puerto | **8000** (el que escucha gunicorn ✓; se puede cambiar con `PORT` ✓) |
| Réplicas | **1** (con `RUN_MIGRATIONS=true` las migraciones solo pueden correr en una réplica ⚠️) |
| Health check | Ruta `/health/` (**verificar en la UI**: el campo donde se configura la ruta del health check ✓) |
| Variables | Las de la tabla de la §8 |

El comando `web` del entrypoint hace esto:

1. si `RUN_MIGRATIONS=true`, aplica las migraciones (`manage.py migrate`) ✓;
2. arranca gunicorn en `0.0.0.0:${PORT:-8000}` con `GUNICORN_WORKERS`
   procesos ✓.

> **El health check no necesita `Host` permitido**: el endpoint `/health/` se
> contesta antes de que Django valide el `Host` ✓ (las plataformas lo llaman
> con la IP interna del servicio ✓). El resto de los endpoints **sí** validan
> el `Host` ✓: `DJANGO_ALLOWED_HOSTS` tiene que traer el dominio público ✓.

## 6. El servicio worker

| Campo | Valor |
|---|---|
| Imagen | La misma del web ✓ |
| Comando | `worker` |
| Puerto | **Ninguno** (no expone nada: es un worker de cola ✓) |
| Réplicas | **1** ⚠️ (con el beat embebido el scheduler no se puede duplicar ✓) |
| Variables | Las de la tabla de la §8, con `CELERY_EMBED_BEAT=true` ✓ |

El comando `worker` del entrypoint arranca celery con:

```
celery -A config worker -l info --concurrency ${CELERY_WORKER_CONCURRENCY} -B
```

- `-B` es el beat embebido ✓: usa el schedule de `config/celery.py` ✓ (las
  cuatro tareas diarias ✓) y escribe su archivo en
  `/var/celerybeat/celerybeat-schedule` ✓.
- **Con el beat embebido, el worker tiene que correr en UNA sola réplica** ⚠️:
  dos réplicas dispararían las tareas dos veces (y el proyecto avisa de esto
  en el modo demo ✓).

## 7. Las variables de entorno

### Servicio web

| Variable | Valor | ¿Secreto? |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | no |
| `DJANGO_SECRET_KEY` | la clave generada | **sí** |
| `DJANGO_DEBUG` | `0` | no |
| `DJANGO_ALLOWED_HOSTS` | el dominio público, separado por comas (**sin `*`**) | no |
| `CORS_ALLOWED_ORIGINS` | la URL de Vercel del front, separada por comas (**sin `*`**) | no |
| `DATABASE_URL` | la cadena de la base administrada | **sí** |
| `DB_SSLMODE` | `require` (si la base lo pide) | no |
| `REDIS_URL` | la URL de la Redis administrada | **sí** |
| `DEMO_MODE` | `true` (demo: dinero simulado y avisos por consola) | no |
| `LEDGER_SIMULATED_DEPOSITS_ENABLED` | `true` (en demo) | no |
| `RUN_MIGRATIONS` | `true` (**solo en el web y con una réplica**) | no |
| `PORT` | `8000` | no |
| `GUNICORN_WORKERS` | `1` (plan gratuito) | no |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | vacíos: los avisos salen por consola ⚠️ | **sí** (si se usa SMTP) |
| `DEFAULT_FROM_EMAIL` | `no-reply@presto.local` | no |

### Servicio worker

Las mismas, **menos** `RUN_MIGRATIONS` y `PORT`, y **más**:

| Variable | Valor | ¿Secreto? |
|---|---|---|
| `CELERY_EMBED_BEAT` | `true` | no |
| `CELERY_WORKER_CONCURRENCY` | `1` (plan gratuito) | no |

> `SECURE_HSTS_SECONDS` y `CSRF_TRUSTED_ORIGINS` se pueden dejar sin definir
> ✓ (el HSTS tiene un default de un año ✓).

## 8. Migrar, superusuario y datos de prueba

Las migraciones las aplica el web al arrancar (`RUN_MIGRATIONS=true` ✓). Para
correr comandos a mano dentro del servicio:

> **verificar en la UI**: cómo se abre una shell (o un comando) dentro de un
> servicio en Northflank. En general es un "command" temporal o una terminal
> del servicio (**no hay acceso desde este repositorio** ⚠️).

Con esa shell (o con un comando temporal):

```sh
# Superusuario para el admin (/admin/)
python manage.py createsuperuser

# Los management commands que existen (no hay comando de seed)
python manage.py mark_overdue_loans
python manage.py settle_investments
```

Para tener **datos de prueba** hay que Approbar el KYC de un usuario y crear un
producto de inversión: los dos los carga **staff desde el admin**
(`/admin/identity/kycverification/` y `/admin/investments/investmentproduct/`)
✓, porque el proyecto los restringe a staff por diseño ✓.

Alternativa (shell del servicio):

```sh
python manage.py shell -c "
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

## 9. Verificar

```sh
# 1. La salud (no necesita token)
curl -s https://<dominio-publico>/health/
# {"status": "ok"}

# 2. El modo de la instancia
curl -s https://<dominio-publico>/api/v1/meta/
# {"mode":"demo","simulated_money":true}

# 3. Un depósito simulado (con el token de un usuario con KYC aprobado)
curl -s -X POST https://<dominio-publico>/api/v1/ledger/transactions/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: primer-deposito" \
  -H "Content-Type: application/json" \
  -d '{"type":"deposit","currency":"ARS","amount":"1000.00"}'

# 4. El preflight CORS desde el origen del front
curl -i -X OPTIONS https://<dominio-publico>/api/v1/ledger/transactions/ \
  -H "Origin: https://<url-de-vercel>" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" | head -20
# access-control-allow-origin: https://<url-de-vercel>
```

Si el preflight no devuelve el header, revisá `CORS_ALLOWED_ORIGINS` (tiene que
ser **exactamente** la URL del front ✓) y que el servicio haya recibido la
variable (los cambios de variables reinician el servicio ✓).

Para comprobar que el proxy manda `X-Forwarded-Proto` (sin eso, la aplicación
redirigiría en loop):

```sh
curl -i https://<dominio-publico>/health/ | head -1     # HTTP/2 200
curl -i http://<dominio-publico>/health/  | head -1      # HTTP/2 301 (a https)
```

## 10. Actualizar la app y ver los logs

- **Actualizar**: `git push` a `main` → la plataforma reconstruye la imagen y
  reinicia los servicios (**verificar en la UI**: si hace falta apretar
  "redeploy" a mano o si el build starts solo ✓).
- **Migraciones**: con `RUN_MIGRATIONS=true` en el web, se aplican solas al
  reiniciar ✓. Si el web tiene **más de una réplica**, sacá la variable y
  corré las migraciones a mano (una sola vez ✓) ⚠️.
- **Logs**: la UI de cada servicio muestra la salida (**verificar en la UI**:
  dónde está exactamente el panel de logs ✓). En modo demo los avisos de las
  notificaciones salen ahí ✓ (buscá `Subject:` ✓).

## 11. Si no alcanza la memoria

El plan gratuito tiene poca RAM ⚠️. Con un solo proceso:

- `GUNICORN_WORKERS=1` y `CELERY_WORKER_CONCURRENCY=1` ✓ (los defaults
  documentados para el plan gratuito ✓).
- **No hay límites de memoria configurados** ✓: un límite duro mata el
  proceso a mitad de una operación de dinero ✗ → es preferible que la
  plataforma avise ✓.
- Si el proceso muere por memoria, el siguiente ajuste es bajar la concurrencia
  a 1 ✓ y revisar que el worker **no** tenga el beat embebido si no hace falta
  ✓ (el beat es un proceso más ✗).

> **verificar en la UI**: los límites de memoria y CPU que ofrece el plan
> gratuito y si se pueden subir.

## 12. Backups

- **Los backups de la base administrada los hace el add-on** de Northflank
  (**verificar en la UI**: dónde deja los respaldos, cada cuánto y cómo se
  restauran ✗ — no hay acceso a esa consola desde acá ⚠️).
- **`deploy/backup-postgres.sh` NO aplica a Northflank** ✗: ese script es del
  compose de producción (levanta su propio `pg_dump` contra el Postgres del
  compose ✓). Contra la base administrada se puede usar `pg_dump` con las
  credenciales de la base, pero el `pg_dump` tiene que estar instalado en la
  máquina desde la que se corra (**verificar en la UI**: si la plataforma
  ofrece backups programados de la base administrada ✓ → usarlos ✓ en lugar
  de `pg_dump` ✗).
- Restaurar un backup del add-on: **verificar en la UI** ⚠️ (el procedimiento
  exacto depende del add-on ✗).

## 13. Límites conocidos del plan gratuito (todo "verificar")

| Límite | Qué hacer |
|---|---|
| Memoria y CPU del servicio | **verificar en la UI**: los límites exactos y si se pueden subir |
| 2 servicios, 2 bases y 2 cron jobs | Ya es el diseño de este despliegue ✓ (web + worker + 2 bases + 2 cron) ✓ |
| Réplicas | El plan gratuito suele dar **una** por servicio ✓ (necesario para el beat embebido ✓) — **verificar en la UI** |
| Sleep / apagado automático | **verificar en la UI**: si el servicio se duerme, el primer request tarda (y el worker no corre ✗) |
| Dominio | **verificar en la UI**: si el plan gratuito da un dominio propio ✗ (si no, hay que poner uno desde Vercel o DuckDNS ✓) |
| Certificados TLS | **verificar en la UI**: si la plataforma termina el TLS ✓ (la aplicación ya reenvía `X-Forwarded-Proto` ✓) |
| Logs | **verificar en la UI**: cuánto tiempo se guardan y si hay que exportarlos |
| Backups de la base | **verificar en la UI**: los del add-on ✓ (§12) |

## 14. Lo que sí se verificó desde acá

Todo esto se comprobó con el **stack local** imitando el entorno de
Northflank (la misma imagen, un Postgres y un Redis de prueba, `web` y
`worker` con `CELERY_EMBED_BEAT=true` ✓):

- la imagen **una sola** sirve para el web y para el worker ✓ (solo cambia el
  comando ✓);
- el web aplica las migraciones al arrancar (`RUN_MIGRATIONS=true` ✓) y
  escucha en `$PORT` ✓;
- `/health/` responde 200 **incluso con el `Host` interno** ✓ (el endpoint se
  contesta antes de la validación ✓) y los demás endpoints siguen devolviendo
  400 con un `Host` desconocido ✓;
- el worker con el beat embebido levanta el schedule del proyecto ✓ (las cuatro
  tareas diarias ✓) y registra las cinco tasks ✓;
- el schedule se escribe en un directorio que el contenedor puede escribir ✓;
- el depósito simulado funciona ✓ y **la suma de los saldos por moneda queda
  en 0** ✓;
- el preflight CORS responde 200 con el origen permitido ✓;
- el admin carga sus estilos ✓ (whitenoise ✓).

Lo que **no** se pudo comprobar (no hay acceso a la consola de Northflank ⚠️):
la interfaz en sí, los límites del plan, los backups del add-on, el panel de
logs y el procedimiento de restauración ✗ → están marcados como "verificar en
la UI" ✓.
