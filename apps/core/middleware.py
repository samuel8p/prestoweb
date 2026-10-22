"""Middleware transversal de la app core."""

from django.conf import settings

HEALTH_PATH = '/health/'


class DemoModeHeaderMiddleware:
    """Agrega la cabecera `X-Presto-Mode` cuando la aplicación está en modo demo.

    Sirve para que el frontend (y quien haga un diagnóstico) sepa de entrada
    que la aplicación corre como demostración y que el dinero es simulado.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEMO_MODE:
            response['X-Presto-Mode'] = 'demo'
        return response


class HealthCheckMiddleware:
    """Contesta `/health/` antes de que Django valide el `Host`.

    Las plataformas mandan el chequeo de salud a la **IP interna** del
    servicio. Django responde 400 cuando el `Host` no está en `ALLOWED_HOSTS`
    (que tiene que quedar cerrado con el dominio público), así que el
    chequeo fallaría y el servicio quedaría marcado como unhealthy.

    El endpoint es público y no dice nada del servicio más que "la base
    contesta", así que se contesta antes de la validación. El resto de los
    endpoints siguen validando el `Host` como siempre.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH:
            from apps.core.views import health_check

            return health_check(request)
        return self.get_response(request)
