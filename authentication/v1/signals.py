"""
authentication.v1.signals

This module contains Django signal receivers for managing user-related events in the authentication system.

It ensures that:
- Every `CustomUser` has an associated `UserProfile`.
- A `ProfileVerification` is created and a verification email is sent upon user registration.
- Users who sign up via social login receive onboarding actions.
- Token expiry handling for profile verification is automatic.
- A password reset email is optionally sent on account creation.

Signals:
    - create_or_update_user_profile
    - social_user_onboarding
    - create_profile_verification
    - handle_token_resend
    - send_password_reset_email

All signal handlers include error handling and logging to avoid crashing the application during signal processing.
"""

import logging
import uuid
from typing import Type

from django.conf import settings
from django.db import transaction
from django.db.models import Model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from allauth.account.signals import user_signed_up

from authentication.models import CustomUser, UserProfile, ProfileVerification
from authentication.v1.tasks.verification_task import send_verification_email_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Ensure a UserProfile exists and is updated when a CustomUser is saved.

    This signal guarantees every user has a profile, creating one if missing.
    It's idempotent and safe to call multiple times.

    Args:
        sender (Model): The model class (`CustomUser`) sending the signal.
        instance (CustomUser): The user instance being saved.
        created (bool): Whether the user was just created.
        **kwargs: Additional keyword arguments.
    """
    try:
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        profile.save()
        logger.info(f"UserProfile ensured for user: {instance.username}")
    except Exception as e:
        logger.error(f"Error creating or updating UserProfile for user {instance.username}: {e}")


@receiver(user_signed_up)
def social_user_onboarding(sender, request, user: CustomUser, **kwargs) -> None:
    """
    Handle additional setup for users who register via social authentication.

    Ensures the user has a UserProfile. Can be extended for more onboarding logic.

    Args:
        sender (Model): The signal sender.
        request (HttpRequest): The request associated with signup.
        user (CustomUser): The newly signed-up user.
        **kwargs: Additional keyword arguments.
    """
    try:
        UserProfile.objects.get_or_create(user=user)
        logger.info(f"Social onboarding ensured for user: {user.username}")
    except Exception as e:
        logger.error(f"Social onboarding failed for user {user.username}: {e}")


@receiver(post_save, sender=CustomUser)
def create_profile_verification(sender: Type[Model], instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Create a ProfileVerification instance and send a verification email after user registration.

    This makes the user inactive, generates a unique token, and sends a verification email.

    Args:
        sender (Model): The model that triggered the signal.
        instance (CustomUser): The newly created user instance.
        created (bool): Whether the user was just created.
        **kwargs: Additional keyword arguments.
    """
    if created:
        try:
            instance.activated_profile = False
            instance.save(update_fields=['activated_profile'])

            verification = ProfileVerification.objects.create(
                user=instance,
                token=uuid.uuid4(),
                created_at=timezone.now(),
                expires_at=timezone.now() + timezone.timedelta(minutes=10),
                used=False
            )

            if settings.CELERY_ALWAYS_EAGER:
                send_verification_email_task(instance.email, verification.token)
            else:
                send_verification_email_task.delay(instance.email, verification.token)

        except Exception as e:
            logger.error(f"Error creating verification for {instance.username}: {e}")


@receiver(pre_save, sender=ProfileVerification)
def handle_token_resend(sender: Type[ProfileVerification], instance: ProfileVerification, **kwargs) -> None:
    """
    Resend a new token and update expiry if an existing token is expired and unused.

    Args:
        sender (Model): The ProfileVerification model class.
        instance (ProfileVerification): The instance being saved.
        **kwargs: Additional keyword arguments.
    """
    if not instance.pk:
        return

    try:
        previous_instance = ProfileVerification.objects.get(pk=instance.pk)

        if instance.token != previous_instance.token:
            send_verification_email_task.delay(instance.user.email, instance.token)
            return

        if previous_instance.is_expired() and not previous_instance.used:
            new_token = str(uuid.uuid4())
            instance.token = new_token
            instance.created_at = timezone.now()
            instance.expires_at = instance.created_at + timezone.timedelta(minutes=10)

            if instance.user and instance.user.email:
                def send_email_after_save():
                    send_verification_email_task.delay(instance.user.email, new_token)
                    logger.info(f"New verification token sent to {instance.user.email}.")

                transaction.on_commit(send_email_after_save)
            else:
                logger.warning(f"Missing user or email for verification ID {instance.pk}")

    except ProfileVerification.DoesNotExist:
        logger.warning(f"ProfileVerification not found for pk={instance.pk}")


@receiver(post_save, sender=CustomUser)
def send_password_reset_email(sender: Type[Model], instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Optionally send a password reset email when a new user is created.

    This signal is usually used for onboarding flows. To disable in tests, mock or patch this method.

    Args:
        sender (Model): The CustomUser model class.
        instance (CustomUser): The newly created user.
        created (bool): Whether this is a new user.
        **kwargs: Additional keyword arguments.
    """
    if created:
        try:
            instance.send_password_reset_email()
        except Exception as e:
            logger.error(f"Error sending password reset email to {instance.email}: {e}")
