# ADR 0009 — El alias público del usuario

- **Estado:** aceptado
- **Fecha:** 2026-10-22
- **Ámbito:** apps `identity` y `ledger`

## Contexto

Para mandarle plata a alguien hay que encontrarlo. El email no sirve: no se
muestra en un perfil y la gente no lo tiene a mano. El alias es el identificador
por el que un usuario se encuentra (y es lo que se pone en el comprobante de
una transferencia).

Eso convierte al alias en un **identificador público**: tiene que ser corto
(fácil de=dictarlo y de recordarlo), fácil de escribir a mano y no puede
confundirse con una ruta de la API, con un rol de administración o con el
soporte.

Al mismo tiempo, el alias no debe filtrar datos: con el alias se puede
encontrar a una persona, y por eso la búsqueda tiene que devolver **lo
mínimo** y estar limitada.

## Decisión

1. **El alias es un campo del usuario** (`identity.User.alias`), nullable: un
   usuario puede no tener alias todavía.
2. **Es único sin distinguir mayúsculas.** La unicidad la garantiza la base
   con un constraint funcional sobre `Lower(alias)` (PostgreSQL trata los NULL
   como distintos: varios usuarios pueden no tener alias ✓). El formato
   obliga a que el alias ya venga en minúsculas, así que la comparación sin
   mayúsculas es la red de seguridad de la base ✓.
3. **El formato es estricto:** de 6 a 20 caracteres, solo minúsculas, dígitos,
   punto, guion o guion bajo, y empieza y termina con una letra o un dígito.
   Se valida en el service (`identity.alias.validate_alias`), no solo en el
   serializer: la regla es de dominio ✓.
4. **Hay una lista de alias reservados** (`admin`, `presto`, `soporte`, `api`,
   `root`, `support`...): palabras que un usuario podría usar para hacerse
   pasar por el soporte o por la administración ✓.
5. **`PUT /api/v1/identity/alias/`** pone o cambia el alias propio: `400` si
   el formato no se cumple o el alias está reservado, `409` si otro usuario ya
   lo tiene ✓. `GET /api/v1/identity/alias/` devuelve el propio (null si no
   tiene) ✓ y el perfil (`GET /api/v1/auth/me/`) también lo trae ✓.
6. **`identity.selectors.get_user_id_by_alias`** resuelve el alias a un
   usuario (sin distinguir mayúsculas) ✓. Es el único punto por el que otra
   app encuentra a un usuario ✓.
7. **`GET /api/v1/ledger/accounts/by-alias/{alias}/`** devuelve **lo mínimo
   para pagarle**: el alias, un nombre reducido (el nombre y la inicial del
   apellido) y las billeteras por moneda (`currency` y `account_id`). **No**
   devuelve el email ni los saldos ✓.
8. **La búsqueda está limitada a 5 por minuto** (`alias_lookup`, más estricta
   que el login) y **pide token**: por el alias se puede averiguar si alguien
   tiene cuenta, así que no es público ✓.
9. Los avisos leídos (`notifications.read_at`) son un cambio **aparte**: no
   tocan la unicidad de los avisos ni el envío ✓.

## Consecuencias

**Positivas**

- Pagar a alguien es escribir su alias.
- El alias se puede mostrar en un comprobante o en un perfil sin exponer el
  email.
- La búsqueda no filtra datos que no le corresponden al que busca.

**Negativas / riesgos asumidos**

- El alias es **público**: cualquiera con token puede saber si un alias existe
  (el 404 lo dice) ✓ → por eso el límite es estricto ✓ y el dato devuelto es
  mínimo ✓.
- El alias ocupa un espacio único: un usuario que quiere uno "bonito" puede
  quedar sin él si otro lo tomó antes ✓ (el 409 lo dice ✓).
- El **importe de la billetera no se ve** en la búsqueda ✓: el que paga tiene
  que fiarse del monto que él pone ✓.
- La lista de alias reservados crece con el tiempo (cada nombre que alguien
  reclama como "oficial" se agrega) ✓.

**Pendiente**

- No hay forma de recuperar un alias olvidado (el usuario tiene que elegir
  otro) ✓: no hay correo de recuperación todavía ✓.
- La búsqueda no devuelve un **avatar** ni nada más que identifique a la
  persona: cuando el front lo necesite, es otro campo aditivo ✓.
- El `read_at` de los avisos no se usa para nada todavía (no hay "vistos no
  leídos" en el front todavía ✓): es el dato, no la funcionalidad ✓.
