"""Coupon Core package."""

from __future__ import absolute_import, unicode_literals

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Import the Celery app if Celery is installed.  Some test environments may not
# have Celery available, so gracefully handle the import error.
try:
    from .celery.celery import app as celery_app
except Exception:  # pragma: no cover - optional dependency
    celery_app = None

__all__ = ('celery_app',) 