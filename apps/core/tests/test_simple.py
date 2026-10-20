import pytest

pytestmark = pytest.mark.django_db


def test_hello_world():
    """Simple test to verify pytest-django is working."""
    assert 'hello' == 'hello'
