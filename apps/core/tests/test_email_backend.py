"""Tests de la elección del backend de email (modo demo)."""

import os
import subprocess
import sys

CONSOLE_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


def read_email_backend(**environment: str) -> str:
    """Devuelve el EMAIL_BACKEND que resuelve Django con ese entorno.

    Se corre en un subproceso con `config.settings.base` para leer los settings
    tal como los ve la aplicación, sin que las variables del entorno del test
    (ni el `--ds` de pytest) los pisen.

    Args:
        environment: variables de entorno para el subproceso.

    Returns:
        El backend configurado.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith('EMAIL_')}
    env.update(environment)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
    result = subprocess.run(
        [sys.executable, '-c', 'from django.conf import settings; print(settings.EMAIL_BACKEND)'],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_without_email_host_the_backend_is_the_console_one():
    """Modo demo: sin EMAIL_HOST los avisos salen por consola (logs del worker)."""
    assert read_email_backend() == CONSOLE_BACKEND


def test_with_email_host_the_backend_is_smtp():
    """Si EMAIL_HOST está definido, el backend por defecto es SMTP."""
    backend = read_email_backend(EMAIL_HOST='smtp.example.com')

    assert backend == SMTP_BACKEND


def test_an_explicit_email_backend_wins():
    """Si se define EMAIL_BACKEND, manda lo explícito."""
    backend = read_email_backend(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')

    assert backend == 'django.core.mail.backends.locmem.EmailBackend'
