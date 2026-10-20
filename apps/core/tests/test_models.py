"""Tests for core.models.BaseModel."""


def test_base_model_has_uuid():
    """Test that BaseModel creates objects with UUID primary key."""
    from apps.core.models import BaseModel
    import uuid

    class TestModel(BaseModel):
        class Meta:
            app_label = "core"

    obj = TestModel()
    assert obj.id is not None
    assert isinstance(obj.id, uuid.UUID)
    assert obj.created_at is not None
    assert obj.updated_at is not None


def test_base_model_timestamps():
    """Test that BaseModel timestamps are set on creation."""
    from apps.core.models import BaseModel
    import uuid
    from datetime import datetime, timezone

    class TestModel(BaseModel):
        class Meta:
            app_label = "core"

    obj = TestModel()
    assert obj.created_at is not None
    assert obj.updated_at is not None
    # Check that created_at is roughly now
    now = datetime.now(timezone.utc)
    assert abs((obj.created_at - now).total_seconds()) < 5


def test_base_model_save_updates_timestamp():
    """Test that saving updates updated_at."""
    from apps.core.models import BaseModel
    import uuid

    class TestModel(BaseModel):
        class Meta:
            app_label = "core"

    obj = TestModel()
    old_updated = obj.updated_at
    obj.save()
    assert obj.updated_at > old_updated