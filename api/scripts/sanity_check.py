"""Throwaway sanity script (not part of the shipped app) confirming
`django.setup()` genuinely works from this separate api/.venv process against
the real backend/ code and its SQLite DB. Run with:

    .venv/Scripts/python.exe scripts/sanity_check.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.django_orm import setup_django  # noqa: E402

setup_django()

from apps.users.models import User  # noqa: E402

print("User.objects.count() =", User.objects.count())
