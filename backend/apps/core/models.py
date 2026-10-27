"""Reusable model mixins shared by every app.

Kept intentionally free of any business logic beyond what's intrinsic to a
model mixin (field definitions, managers, soft-delete querysets). Anything
that mutates domain state belongs in the owning app's ``services.py``.
"""
import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Adds self-managed ``created_at`` / ``updated_at`` timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft-delete every row matched by this queryset."""
        from django.utils import timezone

        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Default manager: excludes soft-deleted rows."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Adds soft-delete behaviour: `is_deleted` rows are hidden by default.

    - ``objects`` (the default manager) excludes soft-deleted rows.
    - ``all_objects`` includes them, for admin/audit/recovery use cases.
    - Calling ``.delete()`` on an instance soft-deletes it; use
      ``.hard_delete()`` to actually remove the row.
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, *args, **kwargs):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


class AuditedModel(models.Model):
    """Adds nullable `created_by` / `updated_by` FKs to the user model.

    Nullable because system/management-command writes (migrations, data
    fixtures, Celery tasks) have no authenticated user to attribute to.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


def uuid4_hex() -> str:
    """Helper kept here for any model wanting a non-PK random token field."""
    return uuid.uuid4().hex
