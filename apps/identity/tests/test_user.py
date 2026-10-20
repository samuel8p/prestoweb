"""Tests for identity.models.User."""


def test_user_has_email_as_login():
    """Test that User model uses email as login field."""
    from apps.identity.models import User

    user = User.objects.create_user(
        email="test@example.com",
        password="testpassword123"
    )

    assert user.email == "test@example.com"
    assert user.username == "test@example.com"
    assert user.check_password("testpassword123")


def test_user_email_unique():
    """Test that user email must be unique."""
    from apps.identity.models import User

    User.objects.create_user(
        email="unique@example.com",
        password="testpassword123"
    )

    from django.db import IntegrityError
    try:
        User.objects.create_user(
            email="unique@example.com",
            password="testpassword123"
        )
        assert False, "Expected IntegrityError"
    except IntegrityError:
        pass


def test_user_str_method():
    """Test that User __str__ returns email."""
    from apps.identity.models import User

    user = User.objects.create_user(
        email="str@example.com",
        password="testpassword123"
    )

    assert str(user) == "str@example.com"