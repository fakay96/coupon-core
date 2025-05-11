"""
authentication.v1.signals

This module contains Django signal receivers for managing user-related events in the authentication system.

It ensures that:
- Every `CustomUser` has an associated `UserProfile`.
- A `ProfileVerification` is created and a verification email is sent upon user registration.
- Users who sign up via social login receive onboarding actions.
- Token expiry handling for profile verification is automatic.

Signals:
    - create_or_update_user_profile
    - social_user_onboarding
    - create_profile_verification
    - handle_token_resend
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from allauth.account.signals import user_signed_up

from authentication.models import CustomUser, UserProfile, ProfileVerification
from authentication.v1.tasks import send_verification_email_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Ensure a UserProfile exists and is updated whenever a CustomUser is saved.
    """
    try:
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        profile.save()
        logger.info(f"UserProfile ensured for user: {instance.username}")
    except Exception as e:
        logger.error(f"Error ensuring UserProfile for {instance.username}: {e}")


@receiver(user_signed_up)
def social_user_onboarding(sender, request, user: CustomUser, **kwargs) -> None:
    """
    Handle setup for users who register via social authentication.
    """
    try:
        UserProfile.objects.get_or_create(user=user)
        logger.info(f"Social onboarding complete for user: {user.username}")
    except Exception as e:
        logger.error(f"Social onboarding failed for {user.username}: {e}")


@receiver(post_save, sender=CustomUser)
def create_profile_verification(sender, instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Create a ProfileVerification and send a verification email after user registration.
    """
    if not created:
        return

    try:
        # Mark user as unverified
        instance.activated_profile = False
        instance.save(update_fields=['activated_profile'])

        # Create verification record
        verification = ProfileVerification.objects.create(
            user=instance,
            token=uuid.uuid4(),
            created_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            used=False
        )

        
        send_verification_email_task.delay(instance.email, verification.token)

    except Exception as e:
        logger.error(f"Error creating ProfileVerification for {instance.username}: {e}")


@receiver(pre_save, sender=ProfileVerification)
def handle_token_resend(sender, instance: ProfileVerification, **kwargs) -> None:
    """
    Resend a new token if the existing one expired and hasn't been used.
    """
    if not instance.pk:
        return

    try:
        previous = ProfileVerification.objects.get(pk=instance.pk)

        # If the token itself changed, send a new email immediately
        if instance.token != previous.token:
            send_verification_email_task.delay(instance.user.email, instance.token)
            return

        # If expired and not used, refresh token and expiry, then send
        if previous.is_expired() and not previous.used:
            new_token = str(uuid.uuid4())
            instance.token = new_token
            instance.created_at = timezone.now()
            instance.expires_at = instance.created_at + timezone.timedelta(minutes=10)

            def on_commit_send():
                send_verification_email_task.delay(instance.user.email, new_token)
                logger.info(f"Resent verification token to {instance.user.email}")

            transaction.on_commit(on_commit_send)

    except ProfileVerification.DoesNotExist:
        logger.warning(f"No previous ProfileVerification for pk={instance.pk}")
    except Exception as e:
        logger.error(f"Error handling token resend for {instance.user.username}: {e}")
