"""
Signals for managing UserProfile creation and updates.

This module ensures every CustomUser has an associated UserProfile and updates it when necessary.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from authentication.models import CustomUser, UserProfile

# Set up logging for debugging and error tracking
logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(
    sender, instance: CustomUser, created: bool, **kwargs
) -> None:
    """
    Signal to create or update a UserProfile whenever a CustomUser instance is saved.

    Args:
        sender: The model class sending the signal.
        instance (CustomUser): The instance of the CustomUser model.
        created (bool): Boolean indicating if a new instance was created.
        **kwargs: Additional keyword arguments.
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
                # Handle rare case where a profile might not exist for an existing user
                UserProfile.objects.create(user=instance)
                logger.warning(
                    f"Missing UserProfile created for user: {instance.username}"
                )
    except Exception as e:
        logger.error(
            f"Error creating or updating UserProfile for user {instance.username}: {e}"
        )
