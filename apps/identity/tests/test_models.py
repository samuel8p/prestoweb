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


def test_create_superuser_rejects_non_staff():
    """El manager de superusuarios rechaza is_staff=False."""
    from apps.identity.models import User

    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email='noadmin@example.com',
            password='TestPass123!',
            is_staff=False,
        )


def test_create_superuser_rejects_non_superuser():
    """El manager de superusuarios rechaza is_superuser=False."""
    from apps.identity.models import User

    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email='noadmin@example.com',
            password='TestPass123!',
            is_superuser=False,
        )


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


def test_profile_is_one_to_one_with_user():
    """Un usuario tiene como máximo un perfil."""
    from apps.identity.models import Profile

    user = UserFactory()
    Profile.objects.create(user=user)

    with pytest.raises(IntegrityError):
        Profile.objects.create(user=user)


def test_profile_fields_are_optional():
    """El perfil se puede crear sin datos cargados."""
    from apps.identity.models import Profile

    user = UserFactory()
    profile = Profile.objects.create(user=user)

    assert profile.phone_number == ''
    assert profile.date_of_birth is None
    assert profile.country == ''


def test_profile_stores_contact_data():
    """El perfil guarda teléfono, fecha de nacimiento y país."""
    from datetime import date

    from apps.identity.models import Profile

    user = UserFactory()
    profile = Profile.objects.create(
        user=user,
        phone_number='+5491133334444',
        date_of_birth=date(1990, 5, 20),
        country='AR',
    )

    assert profile.phone_number == '+5491133334444'
    assert profile.date_of_birth == date(1990, 5, 20)
    assert profile.country == 'AR'


def test_profile_country_rejects_non_iso_code():
    """El país se valida como código ISO 3166-1 alpha-2."""
    from django.core.exceptions import ValidationError

    from apps.identity.models import Profile

    user = UserFactory()
    profile = Profile.objects.create(user=user, country='AR')

    profile.country = 'ar'

    with pytest.raises(ValidationError) as excinfo:
        profile.full_clean()

    assert 'ISO 3166-1' in str(excinfo.value)


def test_profile_str_represents_user():
    """El __str__ del perfil identifica al usuario."""
    from apps.identity.models import Profile

    user = UserFactory()
    profile = Profile.objects.create(user=user)

    assert str(user.id) in str(profile)


def test_kyc_verification_str_represents_user_and_status():
    """El __str__ de la verificación identifica al usuario y el estado."""
    from apps.identity.models import KYCVerification

    user = UserFactory()
    verification = KYCVerification.objects.create(user=user)

    assert str(user.id) in str(verification)
    assert 'pending' in str(verification)


def test_kyc_verification_defaults_to_pending():
    """Una verificación KYC nace en estado pending con fecha de solicitud."""
    from apps.identity.models import KYCVerification

    user = UserFactory()
    verification = KYCVerification.objects.create(user=user)

    assert verification.status == KYCVerification.Status.PENDING
    assert verification.requested_at is not None
    assert verification.resolved_at is None
    assert verification.resolved_by_user_id is None


def test_kyc_verification_documents_default_to_empty():
    """El campo documents arranca vacío."""
    from apps.identity.models import KYCVerification

    user = UserFactory()
    verification = KYCVerification.objects.create(user=user)

    assert verification.documents == {}


def test_kyc_verification_keeps_history_per_user():
    """Un usuario puede tener varias verificaciones resueltas (historial)."""
    from apps.identity.models import KYCVerification

    user = UserFactory()
    KYCVerification.objects.create(user=user, status=KYCVerification.Status.APPROVED)
    KYCVerification.objects.create(user=user, status=KYCVerification.Status.REJECTED)

    assert KYCVerification.objects.filter(user=user).count() == 2


def test_kyc_verification_allows_only_one_pending_per_user():
    """Un usuario no puede tener dos verificaciones pending a la vez."""
    from apps.identity.models import KYCVerification

    user = UserFactory()
    KYCVerification.objects.create(user=user)

    with pytest.raises(IntegrityError):
        KYCVerification.objects.create(user=user)


def test_kyc_verification_resolved_fields_are_optional():
    """Los campos de resolución se completan al resolver la verificación."""
    import uuid

    from apps.identity.models import KYCVerification

    user = UserFactory()
    resolver_id = uuid.uuid4()
    verification = KYCVerification.objects.create(
        user=user,
        status=KYCVerification.Status.APPROVED,
        resolved_by_user_id=resolver_id,
    )

    assert verification.resolved_by_user_id == resolver_id
