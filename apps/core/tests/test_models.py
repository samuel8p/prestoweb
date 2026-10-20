"""Tests for core.models.BaseModel - field definitions only (no DB needed)."""

from apps.core.models import BaseModel
from django.db import models


def test_base_model_has_uuid_field():
    """Test that BaseModel defines UUID primary key field."""
    id_field = BaseModel._meta.get_field("id")
    assert isinstance(id_field, models.UUIDField)
    assert id_field.primary_key is True
    assert id_field.editable is False


def test_base_model_has_created_at_field():
    """Test that BaseModel defines created_at with auto_now_add."""
    created_field = BaseModel._meta.get_field("created_at")
    assert isinstance(created_field, models.DateTimeField)
    assert created_field.auto_now_add is True


def test_base_model_has_updated_at_field():
    """Test that BaseModel defines updated_at with auto_now."""
    updated_field = BaseModel._meta.get_field("updated_at")
    assert isinstance(updated_field, models.DateTimeField)
    assert updated_field.auto_now is True


def test_base_model_is_abstract():
    """Test that BaseModel is abstract."""
    assert BaseModel._meta.abstract is True