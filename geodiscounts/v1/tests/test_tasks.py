"""
Tests for Celery tasks in the Geodiscount API.

This module tests:
1. Discount expiration tasks
2. Notification tasks
3. Analytics tasks
4. Cleanup tasks
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from unittest.mock import patch, MagicMock
from geodiscounts.models import Discount, Retailer
from geodiscounts.v1.tasks import (
    expire_discounts,
    send_discount_notifications,
    update_analytics,
    cleanup_expired_data
)
from django.contrib.gis.geos import Point
from celery.exceptions import Retry

User = get_user_model()

class DiscountExpirationTaskTest(TestCase):
    """Tests for discount expiration task."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() - timedelta(days=1),
            location=Point(0, 0)
        )

    @patch('geodiscounts.v1.tasks.Discount.objects.filter')
    @patch('geodiscounts.v1.tasks.expire_discounts.retry')
    def test_expire_discounts_retry(self, mock_retry, mock_filter):
        """Test retry behavior on task failure."""
        # Make the filter operation raise an exception
        mock_filter.side_effect = Exception('Test error')
        mock_retry.side_effect = Retry('Test error')
        
        with self.assertRaises(Retry):
            expire_discounts()
            
        mock_retry.assert_called_once()

    def test_expire_discounts(self):
        """Test discount expiration task."""
        # Run the task
        expire_discounts()
        
        # Refresh the discount from the database
        self.discount.refresh_from_db()
        
        # Check that the discount is no longer active
        self.assertFalse(self.discount.is_active)


class NotificationTaskTest(TestCase):
    """Tests for notification tasks."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(0, 0)
        )

    @patch('geodiscounts.v1.tasks.Discount.objects.get')
    @patch('geodiscounts.v1.tasks.send_discount_notifications.retry')
    def test_notification_retry(self, mock_retry, mock_get):
        """Test retry behavior for failed notifications."""
        # Make the get operation raise an exception
        mock_get.side_effect = Exception('Test error')
        mock_retry.side_effect = Retry('Test error')
        
        with self.assertRaises(Retry):
            send_discount_notifications(self.discount.id)
            
        mock_retry.assert_called_once()

    @patch('geodiscounts.v1.tasks.send_mail')
    @patch('geodiscounts.models.Discount.get_nearby_users')
    def test_send_discount_notifications(self, mock_get_nearby_users, mock_send_mail):
        """Test sending discount notifications."""
        # Mock nearby users
        nearby_user = User.objects.create_user(
            username='nearby',
            email='nearby@example.com'
        )
        mock_get_nearby_users.return_value = [nearby_user]
        
        # Run the task
        send_discount_notifications(self.discount.id)
        
        # Check that send_mail was called with correct arguments
        mock_send_mail.assert_called_once_with(
            subject='New discount available near you!',
            message=f'Check out this discount from {self.retailer.name}: {self.discount.description}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['nearby@example.com'],
            fail_silently=True
        )


class AnalyticsTaskTest(TestCase):
    """Tests for analytics tasks."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(0, 0)
        )

    @patch('geodiscounts.v1.tasks.Retailer.objects.annotate')
    @patch('geodiscounts.v1.tasks.update_analytics.retry')
    def test_analytics_retry(self, mock_retry, mock_annotate):
        """Test retry behavior for analytics updates."""
        # Make the annotate operation raise an exception
        mock_annotate.side_effect = Exception('Test error')
        mock_retry.side_effect = Retry('Test error')
        
        with self.assertRaises(Retry):
            update_analytics()
            
        mock_retry.assert_called_once()

    def test_update_analytics(self):
        """Test analytics update task."""
        # Run the task
        update_analytics()
        
        # Refresh the retailer from the database
        self.retailer.refresh_from_db()
        
        # Check that analytics data was updated
        self.assertIsNotNone(self.retailer.analytics_data)
        self.assertEqual(self.retailer.analytics_data['total_discounts'], 1)
        self.assertEqual(self.retailer.analytics_data['active_discounts'], 1)
        self.assertEqual(self.retailer.analytics_data['shared_discounts'], 0)
        self.assertEqual(self.retailer.analytics_data['avg_participants'], 0)
        self.assertIn('last_updated', self.retailer.analytics_data)


class CleanupTaskTest(TestCase):
    """Tests for cleanup tasks."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() - timedelta(days=30),
            location=Point(0, 0),
            is_active=True
        )

    @patch('geodiscounts.v1.tasks.Discount.objects.filter')
    @patch('geodiscounts.v1.tasks.cleanup_expired_data.retry')
    def test_cleanup_retry(self, mock_retry, mock_filter):
        """Test retry behavior for cleanup task."""
        # Make the filter operation raise an exception
        mock_filter.side_effect = Exception('Test error')
        mock_retry.side_effect = Retry('Test error')
        
        with self.assertRaises(Retry):
            cleanup_expired_data()
            
        mock_retry.assert_called_once()

    def test_cleanup_expired_data(self):
        """Test cleanup of expired data."""
        # Run the task
        cleanup_expired_data()
        
        # Refresh the discount from the database
        self.discount.refresh_from_db()
        
        # Check that the discount is no longer active
        self.assertFalse(self.discount.is_active) 