import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import BaseModel


class UserManager(BaseUserManager):
    """Manager de User que usa el email como campo de login."""

    def create_user(self, email, password=None, **extra_fields):
        """Crea un usuario con el email como identificador.

        Args:
            email: email único del usuario.
            password: contraseña en texto plano; se hashea antes de guardar.
            **extra_fields: campos adicionales del modelo.

        Raises:
            ValueError: si el email viene vacío.
        """
        if not email:
            raise ValueError('El email es obligatorio para crear un usuario.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Crea un superusuario con is_staff e is_superuser activados.

        Raises:
            ValueError: si se fuerza is_staff o is_superuser en False.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Usuario de Presto: el email es el único campo de login."""

    username = None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Profile(BaseModel):
    """Datos adicionales del usuario."""

    country_validator = RegexValidator(
        regex=r'^[A-Z]{2}$',
        message='El país debe ser un código ISO 3166-1 alpha-2 (ej. AR, US).',
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True, validators=[country_validator])

    def __str__(self):
        return f'Profile<{self.user_id}>'
