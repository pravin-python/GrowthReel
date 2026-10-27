"""Read-only queries for the users app. No mutation lives here."""
from __future__ import annotations

from django.db.models import QuerySet

from apps.users.models import User


def get_user_by_email(email: str) -> User | None:
    """Returns the active User with this email, or None if not found."""
    return User.objects.filter(email__iexact=email).first()


def get_active_users() -> QuerySet[User]:
    """Returns all active (non-disabled) users."""
    return User.objects.filter(is_active=True)
