import factory
from django.contrib.auth import get_user_model

from apps.identity.models import KYCVerification, Profile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory de User con email como único campo de login."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = 'TestPass123!'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', None)
        return model_class.objects.create_user(password=password, **kwargs)


class ProfileFactory(factory.django.DjangoModelFactory):
    """Factory de Profile."""

    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    phone_number = '+5491133334444'
    date_of_birth = factory.LazyAttribute(lambda _: None)
    country = 'AR'


class KYCVerificationFactory(factory.django.DjangoModelFactory):
    """Factory de KYCVerification."""

    class Meta:
        model = KYCVerification

    user = factory.SubFactory(UserFactory)
    status = KYCVerification.Status.PENDING
    documents = factory.LazyAttribute(lambda _: {})
