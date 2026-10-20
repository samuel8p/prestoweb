from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """User model with email as login field."""

    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email