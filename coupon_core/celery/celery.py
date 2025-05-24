""" Celery configuration module for the coupon system.  Sets up the Celery application, loads settings from the Django configuration, and ensures tasks are automatically discovered. """
from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings")

app = Celery("coupon_core")
app.config_from_object("coupon_core.settings", namespace="CELERY")
app.autodiscover_tasks(
    packages=[
        "authentication.v1.tasks",
        "geodiscounts.v1.tasks"
    ]
)
app.conf.broker_connection_retry_on_startup = True

# Configure Celery Beat to use the default scheduler
app.conf.beat_scheduler = 'celery.beat.PersistentScheduler'
app.conf.beat_schedule_filename = 'celerybeat-schedule'

# Add Celery Beat schedule
app.conf.beat_schedule = {
    'process-redis-urls': {
        'task': 'geodiscounts.v1.tasks.tasks.process_redis_urls',
        'schedule': 5.0,  # Run every 60 seconds
        'options': {
            'queue': 'pending_urls_queue',
            'expires': 30  # Task expires after 30 seconds if not picked up
        }
    }
}