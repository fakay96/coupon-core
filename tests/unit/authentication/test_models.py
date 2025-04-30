"""
Test cases for authentication models.

This module tests:
1. CustomUser model functionality
2. UserProfile model functionality
3. PasswordResetRequest model functionality
4. ProfileVerification model functionality
5. Model methods and properties
6. Model constraints and validations
"""

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.test import TestCase
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

from authentication.models import (
    CustomUser, 
    UserProfile, 
    Role, 
    PasswordResetRequest,
    ProfileVerification
)

User = get_user_model()

@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        """Test user creation with valid data."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.check_password("testpass123")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Test superuser creation with valid data."""
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        assert user.username == "admin"
        assert user.email == "admin@example.com"
        assert user.is_staff
        assert user.is_superuser

    def test_user_email_validation(self):
        """Test email validation for user creation."""
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username="testuser",
                email="invalid-email",
                password="testpass123"
            )

    def test_user_password_validation(self):
        """Test password validation for user creation."""
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="123"  # Too short
            )

@pytest.mark.django_db
class TestUserProfile:
    def test_profile_creation(self):
        """Test user profile creation on user creation."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        assert hasattr(user, 'profile')
        assert isinstance(user.profile, UserProfile)

    def test_profile_update(self):
        """Test user profile update."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        user.profile.phone_number = "+1234567890"
        user.profile.save()
        assert user.profile.phone_number == "+1234567890"

@pytest.mark.django_db
class TestRole:
    def test_role_creation(self):
        """Test role creation."""
        role = Role.objects.create(
            name="test_role",
            description="Test role description"
        )
        assert role.name == "test_role"
        assert role.description == "Test role description"

    def test_role_validation(self):
        """Test role validation."""
        with pytest.raises(ValidationError):
            role = Role(
                name="t",  # Too short
                description="Test role description"
            )
            role.full_clean()

@pytest.mark.django_db
class TestPasswordResetRequest:
    """Test suite for PasswordResetRequest model."""
    
    def test_create_password_reset_request(self):
        """Test creating a password reset request."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        reset_request = PasswordResetRequest.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        assert reset_request.user == user
        assert not reset_request.used
        assert not reset_request.is_expired()

    def test_password_reset_expiration(self):
        """Test password reset request expiration."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        reset_request = PasswordResetRequest.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )
        assert reset_request.is_expired()

    def test_mark_as_used(self):
        """Test marking a password reset request as used."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        reset_request = PasswordResetRequest.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        reset_request.mark_as_used()
        assert reset_request.used

    def test_auto_expiration_setting(self):
        """Test automatic expiration time setting."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        reset_request = PasswordResetRequest.objects.create(
            user=user,
            token=uuid.uuid4()
        )
        assert reset_request.expires_at is not None
        assert reset_request.expires_at > timezone.now()

@pytest.mark.django_db
class TestProfileVerification:
    """Test suite for ProfileVerification model."""
    
    def test_create_verification(self):
        """Test creating a profile verification."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        assert verification.user == user
        assert not verification.used
        assert not verification.is_expired()

    def test_verification_expiration(self):
        """Test verification token expiration."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )
        assert verification.is_expired()

    def test_mark_as_used(self):
        """Test marking a verification as used."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        verification.mark_as_used()
        assert verification.used

    def test_resend_new_token(self):
        """Test resending a new verification token."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        old_token = verification.token
        verification.resend_new_token(force_resend=True)
        assert verification.token != old_token
        assert not verification.used
        assert not verification.is_expired()

    def test_resend_new_token_expired(self):
        """Test resending a new token when current one is expired."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )
        old_token = verification.token
        verification.resend_new_token()
        assert verification.token != old_token
        assert not verification.used
        assert not verification.is_expired()

    def test_resend_new_token_used(self):
        """Test resending a new token when current one is used."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        verification = ProfileVerification.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        verification.mark_as_used()
        old_token = verification.token
        verification.resend_new_token(force_resend=True)
        assert verification.token != old_token
        assert not verification.used
        assert not verification.is_expired()

@pytest.mark.django_db
class TestCustomUserEdgeCases:
    """Test suite for CustomUser model edge cases."""
    
    def test_guest_user_creation(self):
        """Test creating a guest user."""
        user = User.objects.create_user(
            username="guest",
            email="guest@example.com",
            password="testpass123",
            is_guest=True
        )
        assert user.is_guest
        assert not user.is_staff
        assert not user.is_superuser

    def test_user_activation(self):
        """Test user profile activation."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        user.activated_profile = True
        user.save()
        assert user.activated_profile

    def test_user_phone_number_validation(self):
        """Test phone number validation."""
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="testpass123",
                phone_number="invalid-phone"
            )

    def test_user_phone_number_unique(self):
        """Test phone number uniqueness."""
        User.objects.create_user(
            username="test1",
            email="test1@example.com",
            password="testpass123",
            phone_number="+1234567890"
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                username="test2",
                email="test2@example.com",
                password="testpass123",
                phone_number="+1234567890"  # Same phone number
            )

@pytest.mark.django_db
class TestUserProfileEdgeCases:
    """Test suite for UserProfile model edge cases."""
    
    def test_profile_preferences(self):
        """Test user profile preferences."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        preferences = {
            "notifications": True,
            "theme": "dark",
            "categories": ["food", "shopping"]
        }
        user.profile.preferences = preferences
        user.profile.save()
        assert user.profile.preferences == preferences

    def test_profile_location(self):
        """Test user profile location."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        location = Point(1.0, 1.0)
        user.profile.location = location
        user.profile.save()
        assert user.profile.location == location

    def test_profile_image(self):
        """Test user profile image."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # Note: In a real test, you would need to create a test image file
        # and use it to test the image field
        assert user.profile.profile_image is None 