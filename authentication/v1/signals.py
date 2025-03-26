"""
Signals for managing UserProfile creation and updates.

This module ensures every CustomUser has an associated UserProfile and updates it when necessary.
It also provides an additional signal for onboarding users who register via social authentication.

Signals:
    - create_or_update_user_profile: Creates or updates a UserProfile when a CustomUser is saved.
    - social_user_onboarding: Performs additional onboarding for users who sign up via social login.

Error Handling:
    All signal receivers are wrapped in try-except blocks to ensure that exceptions are logged and do not interrupt
    the normal flow of the application.
"""

import logging

from django.db.models.signals import post_save,pre_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.conf import settings

from authentication.models import CustomUser, UserProfile, ProfileVerification
from django.db.models import Model
from typing import Type
from django.utils import timezone
import uuid
from authentication.v1.tasks.verification_task import send_verification_email_task
from django.db import transaction
# Set up logging for debugging and error tracking
logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Signal to create or update a UserProfile whenever a CustomUser instance is saved.

    This receiver creates a new UserProfile when a new CustomUser is created. For existing users,
    it attempts to update the associated UserProfile. In the rare case where a profile does not exist for
    an existing user, a new profile is created.

    Args:
        sender: The model class sending the signal.
        instance (CustomUser): The instance of the CustomUser model.
        created (bool): Boolean indicating if a new instance was created.
        **kwargs: Additional keyword arguments.

    Error Handling:
        Any exceptions during the profile creation or update process are caught and logged.
    """
    try:
        if created:
            # Create a new UserProfile for the new CustomUser
            UserProfile.objects.create(user=instance)
            logger.info(f"UserProfile created for user: {instance.username}")
        else:
            # Update the existing UserProfile if it exists
            if hasattr(instance, "profile"):
                instance.profile.save()
                logger.info(f"UserProfile updated for user: {instance.username}")
            else:
                # Handle the rare case where a profile might not exist for an existing user
                UserProfile.objects.create(user=instance)
                logger.warning(f"Missing UserProfile created for user: {instance.username}")
    except Exception as e:
        logger.error(f"Error creating or updating UserProfile for user {instance.username}: {e}")


@receiver(user_signed_up)
def social_user_onboarding(sender, request, user: CustomUser, **kwargs) -> None:
    """
    Signal to perform additional onboarding steps for users who register using social accounts.

    This receiver is triggered when a user signs up via social authentication. It ensures that the new user
    has an associated UserProfile and can be extended to perform further onboarding actions, such as sending
    a welcome email or populating additional profile fields.

    Args:
        sender: The sender of the signal.
        request: The HttpRequest that triggered the signup.
        user (CustomUser): The newly created user instance.
        **kwargs: Additional keyword arguments provided by the signal.

    Error Handling:
        Any exceptions during the onboarding process are caught and logged.
    """
    try:
        # Ensure the user has a UserProfile; create one if it does not exist.
        if not hasattr(user, "profile"):
            UserProfile.objects.create(user=user)
            logger.info(f"Social onboarding: UserProfile created for user: {user.username}")
        else:
            # Optionally, perform additional onboarding steps for social signups here.
            logger.info(f"Social onboarding: UserProfile already exists for user: {user.username}")
    except Exception as e:
        logger.error(f"Social onboarding failed for user {user.username}: {e}")


@receiver(post_save, sender=CustomUser)
def create_profile_verification(sender: Type[Model], instance: CustomUser, created: bool, **kwargs) -> None:
    """
    Signal to create a ProfileVerification instance for a new user and set them as inactive.

    This ensures that when a new `CustomUser` is created, it is initially
    inactive (`is_active=False`), a verification profile is created, and a verification email is sent.

    Args:
        sender (Type[Model]): The model class that triggered the signal (CustomUser).
        instance (CustomUser): The specific instance of CustomUser that was saved.
        created (bool): Indicates whether the instance was created (True) or updated (False).
        **kwargs: Additional keyword arguments passed by Django's signal mechanism.

    Returns:
        None
    """
    if created:
        # Ensure the user is inactive at creation
        instance.activated_profile = False
        instance.save(update_fields=['activated_profile'])

        # Create a new ProfileVerification instance with a fresh token
        verification = ProfileVerification.objects.create(
            user=instance,
            token=uuid.uuid4(),
            created_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),  # 10-minute expiration
            used=False
        )

        # Send verification email after creating the token
        if settings.CELERY_ALWAYS_EAGER:
            # If in test mode, execute task synchronously
            send_verification_email_task(instance.email, verification.token)
        else:
            # In production, use Celery
            send_verification_email_task.delay(instance.email, verification.token)
        
@receiver(pre_save, sender=ProfileVerification)
def handle_token_resend(sender: Type[ProfileVerification], instance: ProfileVerification, **kwargs) -> None:
    """
    Signal to handle token renewal and email resend when a ProfileVerification instance is updated.
    
    This ensures that if a `ProfileVerification` instance:
    1. Has NOT been used (`used=False`).
    2. The token HAS expired (`is_expired() == True`).
    3. The token field is CHANGING (new token being issued).
    
    Then:
    - A new token is generated.
    - The expiration time is reset.
    - The instance is updated BEFORE sending the email.
    - The verification email is sent with the new token.
    
    Args:
        sender (Type[Model]): The model class that triggered the signal.
        instance (ProfileVerification): The ProfileVerification instance being updated.
        **kwargs: Additional keyword arguments passed by Django's signal mechanism.
    
    Returns:
        None
    """
    
    # Skip for new instances being created
    if not instance.pk:
        return
    
    try:
        # Get the previous state of the instance
        previous_instance = ProfileVerification.objects.get(pk=instance.pk)
        
        # Case 1: Token was already changed externally
        if instance.token != previous_instance.token:
            logger.debug(f"Token for user {instance.user.email} was already updated externally.")
            # We should use instance.token here, not new_token (which isn't defined yet)
            send_verification_email_task.delay(instance.user.email, instance.token)
            return
        
        # Case 2: Token needs renewal (is expired and not used)
        if previous_instance.is_expired() and not previous_instance.used:
            # Generate new token
            new_token = str(uuid.uuid4())
            
            # Update instance with a new token and reset expiration
            instance.token = new_token
            instance.created_at = timezone.now()
            instance.expires_at = instance.created_at + timezone.timedelta(minutes=10)
            
            # Ensure user exists before sending email (will be sent after save)
            if instance.user and instance.user.email:
                logger.info(f"Token expired for {instance.user.email}. New token generated and will be sent.")
                # We'll schedule this task, but the email will be sent after the save completes
                # to ensure the database is updated first
                def send_email_after_save():
                    send_verification_email_task.delay(instance.user.email, new_token)
                    logger.info(f"New verification token sent to {instance.user.email}.")
                
                # Use transaction.on_commit to ensure email is sent after successful save
                transaction.on_commit(send_email_after_save)
            else:
                logger.warning(f"Failed to send verification email: User or email is missing for {instance.pk}.")
    
    except ProfileVerification.DoesNotExist:
        logger.warning(f"ProfileVerification instance not found for pk={instance.pk}. Skipping signal.")
        
        
