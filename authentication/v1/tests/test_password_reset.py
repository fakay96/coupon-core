from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from authentication.models import CustomUser, PasswordResetRequest
from unittest.mock import patch
from django.utils import timezone
import uuid

class PasswordResetAPITestCase(APITestCase):
    def setUp(self):
        self.user_email = "testuser@example.com"
        self.user_password = "TestPassword123"
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email=self.user_email,
            password=self.user_password,
            activated_profile=True,
        )
        self.url = reverse("auth:password-reset")

    @patch("authentication.v1.tasks.verification_task.send_password_reset_email_task.delay")
    def test_password_reset_request_creates_token_and_sends_email(self, mock_send_email_task):
        """
        Test that a password reset request creates a PasswordResetRequest with a new token
        and enqueues the email sending task.
        """
        response = self.client.post(self.url, {"email": self.user_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Password reset email sent.")

        # Check that a PasswordResetRequest was created
        reset_requests = PasswordResetRequest.objects.filter(user=self.user)
        self.assertEqual(reset_requests.count(), 1)
        reset_request = reset_requests.first()

        # Check that the token is a valid UUID
        try:
            uuid_obj = uuid.UUID(str(reset_request.token))
        except ValueError:
            self.fail("PasswordResetRequest token is not a valid UUID")

        # Check that the email sending task was called with correct arguments
        mock_send_email_task.assert_called_once_with(self.user_email, str(reset_request.token))

    def test_password_reset_request_with_invalid_email(self):
        """
        Test that a password reset request with an invalid email returns a 400 error.
        """
        response = self.client.post(self.url, {"email": "nonexistent@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_password_reset_request_missing_email(self):
        """
        Test that a password reset request without an email returns a 400 error.
        """
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
