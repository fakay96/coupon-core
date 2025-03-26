"""Background tasks for the geodiscounts app."""

from datetime import datetime
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Avg, F, Q
from geodiscounts.models import Discount, SharedDiscount, Retailer
from coupon_core.celery import celery_app  as app

@app.task(bind=True, max_retries=3)
def cleanup_expired_data(self):
    """Clean up expired discounts and shared discounts."""
    try:
        now = timezone.now()
        
        # Clean up expired discounts
        expired_discounts = Discount.objects.filter(
            expiration_date__lt=now,
            is_active=True
        )
        expired_count = expired_discounts.update(is_active=False)
        
        # Clean up expired shared discounts
        expired_shared = SharedDiscount.objects.filter(
            discount__expiration_date__lt=now,
            status='active'
        )
        shared_count = expired_shared.update(status='expired')
        
        return {
            'expired_discounts': expired_count,
            'expired_shared_discounts': shared_count
        }
    except Exception as exc:
        self.retry(exc=exc)

@app.task(bind=True, max_retries=3)
def expire_discounts(self):
    """Expire discounts that have passed their expiration date."""
    try:
        now = timezone.now()
        expired_discounts = Discount.objects.filter(
            expiration_date__lt=now,
            is_active=True
        )
        expired_count = expired_discounts.update(is_active=False)
        return expired_count
    except Exception as exc:
        self.retry(exc=exc)

@app.task(bind=True, max_retries=3)
def notify_expiring_discounts(self, days_threshold=7):
    """Notify retailers of discounts that will expire soon.
    
    Args:
        days_threshold (int): Number of days before expiration to send notification
    """
    try:
        threshold_date = timezone.now() + timezone.timedelta(days=days_threshold)
        expiring_discounts = Discount.objects.filter(
            expiration_date__lte=threshold_date,
            expiration_date__gt=timezone.now(),
            is_active=True
        )
        
        for discount in expiring_discounts:
            send_mail(
                subject=f'Discount {discount.discount_code} expiring soon',
                message=f'Your discount {discount.discount_code} will expire on {discount.expiration_date}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[discount.retailer.contact_info],
                fail_silently=True
            )
    except Exception as exc:
        self.retry(exc=exc)

@app.task(bind=True, max_retries=3)
def send_discount_notifications(self, discount_id):
    """Send notifications to users about a discount.
    
    Args:
        discount_id (int): ID of the discount to send notifications for
    """
    try:
        discount = Discount.objects.get(id=discount_id)
        # Get users within the discount's radius
        nearby_users = discount.get_nearby_users()
        
        for user in nearby_users:
            send_mail(
                subject=f'New discount available near you!',
                message=f'Check out this discount from {discount.retailer.name}: {discount.description}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
    except Exception as exc:
        self.retry(exc=exc)

@app.task(bind=True, max_retries=3)
def update_shared_discount_status(self):
    """Update status of shared discounts based on participant count."""
    try:
        shared_discounts = SharedDiscount.objects.filter(status='PENDING')
        
        for shared_discount in shared_discounts:
            if len(shared_discount.participants) >= shared_discount.min_participants:
                shared_discount.status = 'ACTIVE'
                shared_discount.save()
            elif shared_discount.created_at + timezone.timedelta(days=7) < timezone.now():
                shared_discount.status = 'EXPIRED'
                shared_discount.save()
    except Exception as exc:
        self.retry(exc=exc)

@app.task(bind=True, max_retries=3)
def update_analytics(self):
    """Update analytics data for retailers and discounts."""
    try:
        now = timezone.now()
        # Calculate retailer analytics
        retailers = Retailer.objects.annotate(
            total_discounts=Count('discounts'),
            active_discounts=Count(
                'discounts',
                filter=Q(discounts__expiration_date__gt=now) & Q(discounts__is_active=True)
            ),
            shared_discounts=Count(
                'discounts__shared_discounts',
                filter=Q(discounts__shared_discounts__status='ACTIVE')
            ),
            avg_participants=Avg('discounts__shared_discounts__participants__len')
        )
        
        for retailer in retailers:
            # Store analytics data
            retailer.analytics_data = {
                'total_discounts': retailer.total_discounts,
                'active_discounts': retailer.active_discounts,
                'shared_discounts': retailer.shared_discounts,
                'avg_participants': float(retailer.avg_participants or 0),
                'last_updated': now.isoformat()
            }
            retailer.save(update_fields=['analytics_data'])
    except Exception as exc:
        self.retry(exc=exc) 