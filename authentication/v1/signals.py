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

from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up

from authentication.models import CustomUser, UserProfile

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
