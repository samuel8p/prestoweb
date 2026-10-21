"""Middleware transversal de la app core."""

from django.conf import settings


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
