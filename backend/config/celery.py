"""Celery application factory for GrowthReel.

The other process (the FastAPI ``api/`` service) does not import this module;
it is used only by the Django side (and by a worker process run with
``celery -A config worker``). It reads configuration from Django settings
using the ``CELERY_`` namespace, so all Celery settings live in
``config/settings/*.py`` as ``CELERY_*`` keys.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("growthreel")

# Read config from Django settings, using the CELERY_ namespace so that all
# celery-related settings must start with `CELERY_` in settings files.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py modules in each installed app.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):  # pragma: no cover - diagnostic helper only
    print(f"Request: {self.request!r}")
