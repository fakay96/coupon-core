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
import pytest
from celery import shared_task
from geodiscounts.models import Location
from geodiscounts.v1.tasks import (
    cleanup_expired_discounts,
    notify_discount_expiration,
    update_discount_status,
    process_location_updates,
    sync_merchant_discounts
)

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


@pytest.mark.django_db
class TestDiscountTasks:
    """Test suite for discount-related tasks."""

    @pytest.fixture
    def setup_discounts(self):
        """Set up test discounts."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        
        # Create active discount
        active_discount = Discount.objects.create(
            retailer=retailer,
            description="Active Discount",
            discount_code="ACTIVE123",
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        
        # Create expired discount
        expired_discount = Discount.objects.create(
            retailer=retailer,
            description="Expired Discount",
            discount_code="EXPIRED123",
            expiration_date=timezone.now() - timedelta(days=1),
            location=Point(1.0, 1.0)
        )
        
        return active_discount, expired_discount

    def test_cleanup_expired_discounts(self, setup_discounts):
        """Test cleanup of expired discounts."""
        active_discount, expired_discount = setup_discounts
        
        # Run cleanup task
        cleanup_expired_discounts.delay()
        
        # Verify expired discount is deactivated
        expired_discount.refresh_from_db()
        assert not expired_discount.is_active
        
        # Verify active discount remains active
        active_discount.refresh_from_db()
        assert active_discount.is_active

    @patch('geodiscounts.v1.tasks.send_notification')
    def test_notify_discount_expiration(self, mock_send_notification, setup_discounts):
        """Test discount expiration notifications."""
        active_discount, expired_discount = setup_discounts
        
        # Run notification task
        notify_discount_expiration.delay()
        
        # Verify notification was sent for expired discount
        mock_send_notification.assert_called_once_with(
            expired_discount.retailer.contact_info,
            f"Discount {expired_discount.discount_code} has expired"
        )

    def test_update_discount_status(self, setup_discounts):
        """Test discount status updates."""
        active_discount, expired_discount = setup_discounts
        
        # Run status update task
        update_discount_status.delay()
        
        # Verify status updates
        active_discount.refresh_from_db()
        expired_discount.refresh_from_db()
        
        assert active_discount.status == "active"
        assert expired_discount.status == "expired"


@pytest.mark.django_db
class TestLocationTasks:
    """Test suite for location-related tasks."""

    @pytest.fixture
    def setup_locations(self):
        """Set up test locations."""
        locations = []
        for i in range(3):
            location = Location.objects.create(
                name=f"Test Location {i}",
                latitude=40.7128 + (i * 0.01),
                longitude=-74.0060 + (i * 0.01),
                radius=1000
            )
            locations.append(location)
        return locations

    def test_process_location_updates(self, setup_locations):
        """Test processing of location updates."""
        locations = setup_locations
        
        # Run location update task
        process_location_updates.delay()
        
        # Verify location updates
        for location in locations:
            location.refresh_from_db()
            assert location.last_updated is not None

    def test_location_cleanup(self, setup_locations):
        """Test cleanup of invalid locations."""
        locations = setup_locations
        
        # Mark one location as invalid
        locations[0].is_valid = False
        locations[0].save()
        
        # Run cleanup task
        from geodiscounts.v1.tasks import cleanup_invalid_locations
        cleanup_invalid_locations.delay()
        
        # Verify invalid location is deleted
        with pytest.raises(Location.DoesNotExist):
            Location.objects.get(id=locations[0].id)
        
        # Verify valid locations remain
        assert Location.objects.filter(id=locations[1].id).exists()
        assert Location.objects.filter(id=locations[2].id).exists()


@pytest.mark.django_db
class TestMerchantTasks:
    """Test suite for merchant-related tasks."""

    @pytest.fixture
    def setup_merchant_data(self):
        """Set up test merchant data."""
        retailer = Retailer.objects.create(
            name="Test Merchant",
            contact_info="merchant@example.com",
            location=Point(1.0, 1.0)
        )
        return retailer

    @patch('geodiscounts.v1.tasks.sync_with_merchant_api')
    def test_sync_merchant_discounts(self, mock_sync, setup_merchant_data):
        """Test synchronization with merchant API."""
        retailer = setup_merchant_data
        
        # Mock API response
        mock_sync.return_value = [
            {
                'code': 'MERCH123',
                'value': 10.0,
                'expires_at': (timezone.now() + timedelta(days=7)).isoformat()
            }
        ]
        
        # Run sync task
        sync_merchant_discounts.delay(retailer.id)
        
        # Verify sync was called
        mock_sync.assert_called_once_with(retailer.id)
        
        # Verify discount was created
        assert Discount.objects.filter(
            retailer=retailer,
            discount_code='MERCH123'
        ).exists()

    def test_merchant_discount_cleanup(self, setup_merchant_data):
        """Test cleanup of merchant discounts."""
        retailer = setup_merchant_data
        
        # Create some discounts
        for i in range(3):
            Discount.objects.create(
                retailer=retailer,
                description=f"Test Discount {i}",
                discount_code=f"TEST{i}",
                expiration_date=timezone.now() + timedelta(days=7),
                location=Point(1.0, 1.0)
            )
        
        # Run cleanup task
        from geodiscounts.v1.tasks import cleanup_merchant_discounts
        cleanup_merchant_discounts.delay(retailer.id)
        
        # Verify discounts are cleaned up
        assert Discount.objects.filter(retailer=retailer).count() == 0


@pytest.mark.django_db
class TestTaskErrorHandling:
    """Test suite for task error handling."""

    def test_task_retry_on_failure(self):
        """Test task retry mechanism on failure."""
        with patch('geodiscounts.v1.tasks.cleanup_expired_discounts.retry') as mock_retry:
            # Simulate failure
            mock_retry.side_effect = Exception("Task failed")
            
            # Run task
            cleanup_expired_discounts.delay()
            
            # Verify retry was called
            mock_retry.assert_called_once()

    def test_task_error_logging(self):
        """Test task error logging."""
        with patch('geodiscounts.v1.tasks.logger.error') as mock_logger:
            # Simulate error
            with patch('geodiscounts.v1.tasks.cleanup_expired_discounts') as mock_task:
                mock_task.side_effect = Exception("Task error")
                
                # Run task
                cleanup_expired_discounts.delay()
                
                # Verify error was logged
                mock_logger.assert_called_once()

    def test_task_dependency_handling(self):
        """Test task dependency handling."""
        with patch('geodiscounts.v1.tasks.chain') as mock_chain:
            # Run dependent tasks
            from geodiscounts.v1.tasks import process_discount_updates
            process_discount_updates.delay()
            
            # Verify task chain was created
            mock_chain.assert_called_once() 