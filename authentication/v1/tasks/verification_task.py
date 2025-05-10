from coupon_core.celery import celery_app  as app
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging
from django.db import transaction
from django.utils import timezone
from authentication.models import CustomUser, ProfileVerification

import uuid
logger = logging.getLogger(__name__)

@app.task
def send_verification_email_task(user_email: str, token: str, logo_url: str = None) -> None:
    """
    Celery task to send a verification email asynchronously using an HTML-styled template.

    Args:
        user_email (str): The recipient's email address.
        token (str): The verification token.
        logo_url (str, optional): URL of the company logo to include in the email.

    Returns:
        None
    """
    try:
        subject: str = "Verify Your Account"
        verification_link: str = f"{settings.FRONTEND_DOMAIN_NAME}/auth/verification?token={token}&email={user_email}&mode=activation"

        # Context for template rendering
        context = {
            "token": token,
            "verification_link": verification_link,
            "logo_url": logo_url or f"/static/logo.png",
        }
  

        # Render both HTML and plain-text versions of the email
        html_message: str = render_to_string("emails/verification_email.html", context)
        plain_message: str = render_to_string("emails/verification_email.txt", context)

        from_email: str = settings.DEFAULT_FROM_EMAIL

        # Create email with both HTML and plain-text content
        email = EmailMultiAlternatives(subject, plain_message, from_email, [user_email])
        email.attach_alternative(html_message, "text/html")  # Attach HTML version
        email.send()

        logger.info(f"Verification email sent successfully to {user_email}")

    except Exception as e:
        logger.error(f"Error sending verification email to {user_email}: {str(e)}")

@app.task
def send_password_reset_email_task(user_email: str, token: str, logo_url: str = None) -> None:
    """
    Celery task to send a password reset email asynchronously using an HTML-styled template.

    Args:
        user_email (str): The recipient's email address.
        token (str): The password reset token.
        logo_url (str, optional): URL of the company logo to include in the email.

    Returns:
        None
    """
    try:
        subject: str = "Password Reset Request"
        reset_link: str = f"{settings.FRONTEND_DOMAIN_NAME}/auth/verification?token={token}&email={user_email}&mode=reset"

        # Context for template rendering
        context = {
            "token": token,
            "reset_link": reset_link,
            "logo_url": logo_url or f"/static/logo.png",
        }

        # Render both HTML and plain-text versions of the email
        html_message: str = render_to_string("emails/password_reset_email.html", context)
        plain_message: str = render_to_string("emails/password_reset_email.txt", context)

        from_email: str = settings.DEFAULT_FROM_EMAIL

        # Create email with both HTML and plain-text content
        email = EmailMultiAlternatives(subject, plain_message, from_email, [user_email])
        email.attach_alternative(html_message, "text/html")  # Attach HTML version
        email.send()

        logger.info(f"Password reset email sent successfully to {user_email}")

    except Exception as e:
        logger.error(f"Error sending password reset email to {user_email}: {str(e)}")


@app.task
def resend_verification_token_task(user_email: str, logo_url: str = None) -> None:
    """
    Celery task to force‐resend an account verification token.

    This task will:
      1. Look up the user by email.
      2. Invalidate any existing unused ProfileVerification records.
      3. Create a new ProfileVerification with a fresh token and expiry.
      4. Send the verification email using the same templates as the initial send.

    Args:
        user_email (str): The recipient's email address.
        logo_url (str, optional): URL of the company logo to include in the email.

    Returns:
        None
    """
   

    try:
        # 1. Find the user
        user = CustomUser.objects.get(email__iexact=user_email)

        # 2. Invalidate existing verifications
        ProfileVerification.objects.filter(user=user, used=False).update(used=True)

        # 3. Create a fresh verification record
        now = timezone.now()
        new_verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            created_at=now,
            expires_at=now + timezone.timedelta(minutes=10),
            used=False
        )

        # 4. Send email
        verification_link = f"{settings.FRONTEND_DOMAIN_NAME}/auth/verification?token={new_verification.token}&email={user_email}&mode=activation"
        context = {
            "token": new_verification.token,
            "verification_link": verification_link,
            "logo_url": logo_url or "/static/logo.png",
        }
        html_message = render_to_string("emails/verification_email.html", context)
        plain_message = render_to_string("emails/verification_email.txt", context)
        email = EmailMultiAlternatives(
            subject="Verify Your Account",
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

        logger.info(f"Resent verification token to {user_email}")

    except CustomUser.DoesNotExist:
        logger.warning(f"Cannot resend token: no user with email {user_email}")
    except Exception as e:
        logger.error(f"Error in resend_verification_token_task for {user_email}: {e}")
