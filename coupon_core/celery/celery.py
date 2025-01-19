"""
Celery configuration module for the election system.

Sets up the Celery application, loads settings from the Django configuration,
and ensures tasks are automatically discovered.
"""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings")

app = Celery("coupon_core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True
