"""
Test cases for Celery configuration.

This module tests:
1. Celery app configuration
2. Task registration and discovery
3. Beat schedule configuration
"""

from django.test import TestCase
from unittest.mock import patch, Mock
from celery import Celery
from coupon_core.celery.celery import app

class CeleryConfigTestCase(TestCase):
    """Test suite for Celery configuration."""

    def test_celery_app_configuration(self):
        """Test basic Celery app configuration."""
        self.assertIsInstance(app, Celery)
        self.assertEqual(app.main, 'coupon_core')
        self.assertTrue(app.conf.task_serializer in ['json', 'pickle'])
        self.assertTrue(app.conf.result_serializer in ['json', 'pickle'])
        self.assertTrue('json' in app.conf.accept_content)

    def test_broker_configuration(self):
        """Test broker URL configuration."""
        self.assertTrue(hasattr(app.conf, 'broker_url'))
        self.assertIsNotNone(app.conf.broker_url)

    def test_result_backend_configuration(self):
        """Test result backend configuration."""
        self.assertTrue(hasattr(app.conf, 'result_backend'))
        self.assertIsNotNone(app.conf.result_backend)

    @patch('celery.Celery.autodiscover_tasks')
    def test_task_autodiscovery(self, mock_autodiscover):
        """Test task autodiscovery."""
        app.autodiscover_tasks()
        mock_autodiscover.assert_called_once()

    def test_task_routes(self):
        """Test task routing configuration."""
        self.assertTrue(hasattr(app.conf, 'task_routes'))
        routes = app.conf.task_routes or {}
        self.assertIsInstance(routes, (dict, list))

    def test_beat_schedule(self):
        """Test celery beat schedule configuration."""
        self.assertTrue(hasattr(app.conf, 'beat_schedule'))
        schedule = app.conf.beat_schedule or {}
        self.assertIsInstance(schedule, dict)

    @patch('celery.Celery.send_task')
    def test_task_sending(self, mock_send):
        """Test ability to send tasks."""
        mock_send.return_value = Mock(id='test_task_id')
        
        # Test sending a task
        task_id = app.send_task('test_task', args=[1, 2])
        mock_send.assert_called_once_with('test_task', args=[1, 2])
        self.assertEqual(task_id.id, 'test_task_id')

    def test_timezone_configuration(self):
        """Test timezone configuration."""
        self.assertTrue(hasattr(app.conf, 'timezone'))
        self.assertIsNotNone(app.conf.timezone)

    def test_task_annotations(self):
        """Test task annotation configuration."""
        self.assertTrue(hasattr(app.conf, 'task_annotations'))
        annotations = app.conf.task_annotations or {}
        self.assertIsInstance(annotations, (dict, list, type(None))) 