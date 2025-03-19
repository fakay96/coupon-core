from coupon_core.celery import celery_app  as app
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from coupon_core.settings import (
    BASE_DOMAIN,
    DEFAULT_FROM_EMAIL
)
import logging

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
        verification_link: str = f"{BASE_DOMAIN}authentication/v1/activate/?token={token}&email={user_email}"

        # Context for template rendering
        context = {
            "token": token,
            "verification_link": verification_link,
            "logo_url": logo_url or f"/static/logo.png",
        }
  

        # Render both HTML and plain-text versions of the email
        html_message: str = render_to_string("emails/verification_email.html", context)
        plain_message: str = render_to_string("emails/verification_email.txt", context)

        from_email: str = DEFAULT_FROM_EMAIL

        # Create email with both HTML and plain-text content
        email = EmailMultiAlternatives(subject, plain_message, from_email, [user_email])
        email.attach_alternative(html_message, "text/html")  # Attach HTML version
        email.send()

        logger.info(f"Verification email sent successfully to {user_email}")

    except Exception as e:
        logger.error(f"Error sending verification email to {user_email}: {str(e)}")
