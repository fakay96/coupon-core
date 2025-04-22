"""Celery configuration for the search worker."""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discountcrawlers.settings')

app = Celery('discountcrawlers')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Configure task routes
app.conf.task_routes = {
    'discountcrawlers.services.search_worker.process_search_request': {
        'queue': 'search_queue',
        'routing_key': 'search.request'
    }
}

# Configure task timeouts
app.conf.task_time_limit = 300  # 5 minutes
app.conf.task_soft_time_limit = 240  # 4 minutes

# Configure task retries
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.task_default_retry_delay = 60  # 1 minute
app.conf.task_max_retries = 3

# Configure result backend
app.conf.result_backend = 'redis://localhost:6379/0'
app.conf.result_expires = 3600  # 1 hour

# Configure broker settings
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.broker_connection_retry_on_startup = True

@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}') 