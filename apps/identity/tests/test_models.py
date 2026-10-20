import uuid

import pytest
from django.db import IntegrityError

from apps.identity.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_model_has_no_username_field():
    """El modelo User no expone el campo username heredado de AbstractUser."""
    from apps.identity.models import User

    field_names = {field.name for field in User._meta.get_fields()}

    assert 'username' not in field_names


def test_user_id_is_uuid():
    """La clave primaria del usuario es un UUID."""
    user = UserFactory()

    assert isinstance(user.id, uuid.UUID)


def test_create_user_requires_email():
    """El manager exige un email para crear usuarios."""
    from apps.identity.models import User

    with pytest.raises(ValueError):
        User.objects.create_user(email='', password='TestPass123!')


def test_create_user_sets_password():
    """El manager hashea la contraseña y permite verificarla."""
    from apps.identity.models import User

    user = User.objects.create_user(email='nuevo@example.com', password='TestPass123!')

    assert user.email == 'nuevo@example.com'
    assert user.password != 'TestPass123!'
    assert user.check_password('TestPass123!')


def test_create_superuser_sets_staff_and_superuser():
    """El manager de superusuarios marca is_staff e is_superuser."""
    from apps.identity.models import User

    admin = User.objects.create_superuser(email='admin@example.com', password='TestPass123!')

    assert admin.is_staff is True
    assert admin.is_superuser is True


def test_user_email_is_unique():
    """No se pueden crear dos usuarios con el mismo email."""
    from apps.identity.models import User

    UserFactory(email='duplicado@example.com')

    with pytest.raises(IntegrityError):
        User.objects.create_user(email='duplicado@example.com', password='TestPass123!')


def test_user_str_returns_email():
    """El __str__ del usuario devuelve el email."""
    user = UserFactory(email='str@example.com')

    assert str(user) == 'str@example.com'
