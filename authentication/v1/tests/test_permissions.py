"""
Test cases for authentication permissions.

This module tests:
1. Custom permission classes
2. Role-based access control
3. Object-level permissions
4. Permission inheritance
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.permissions import BasePermission

from django.contrib.auth import get_user_model
from authentication.models import Role, UserProfile
from authentication.v1.permissions import (
    IsAdmin,
    IsOwner,
    IsVerified,
    HasRole,
    ReadOnly
)

User = get_user_model()

class BasePermissionTestCase(APITestCase):
    """Base test case with common setup."""

    def setUp(self):
        """Set up test data."""
        # Create roles
        self.admin_role = Role.objects.create(name='admin')
        self.manager_role = Role.objects.create(name='manager')
        self.user_role = Role.objects.create(name='user')

        # Create users
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!',
            is_staff=True,
            is_active=True
        )
        self.admin.roles.add(self.admin_role)

        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='ManagerPass123!',
            is_active=True
        )
        self.manager.roles.add(self.manager_role)

        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='UserPass123!',
            is_active=True
        )
        self.user.roles.add(self.user_role)

        self.inactive_user = User.objects.create_user(
            username='inactive',
            email='inactive@example.com',
            password='InactivePass123!',
            is_active=False
        )

class AdminPermissionTestCase(BasePermissionTestCase):
    """Test suite for admin permissions."""

    def test_admin_access(self):
        """Test admin access to protected endpoints."""
        self.client.force_authenticate(user=self.admin)
        
        # Test admin endpoints
        urls = [
            reverse('v1:admin-users'),
            reverse('v1:admin-roles'),
            reverse('v1:admin-settings')
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_access_denied(self):
        """Test non-admin access to admin endpoints."""
        users = [self.manager, self.user, self.inactive_user]
        urls = [
            reverse('v1:admin-users'),
            reverse('v1:admin-roles'),
            reverse('v1:admin-settings')
        ]

        for test_user in users:
            self.client.force_authenticate(user=test_user)
            for url in urls:
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crud_operations(self):
        """Test admin CRUD operations."""
        self.client.force_authenticate(user=self.admin)
        
        # Create user
        url = reverse('v1:admin-users')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data['id']

        # Read user
        response = self.client.get(f"{url}{user_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update user
        response = self.client.patch(f"{url}{user_id}/", {'is_active': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete user
        response = self.client.delete(f"{url}{user_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

class OwnerPermissionTestCase(BasePermissionTestCase):
    """Test suite for owner permissions."""

    def setUp(self):
        """Set up additional test data."""
        super().setUp()
        self.user_profile = UserProfile.objects.get(user=self.user)

    def test_owner_access(self):
        """Test owner access to own resources."""
        self.client.force_authenticate(user=self.user)
        
        # Test profile access
        url = reverse('v1:userprofile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test profile update
        response = self.client.patch(url, {'bio': 'Updated bio'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_access_denied(self):
        """Test non-owner access to resources."""
        self.client.force_authenticate(user=self.manager)
        
        # Try to access another user's profile
        url = f"{reverse('v1:userprofile')}?user_id={self.user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_override(self):
        """Test admin override of owner permissions."""
        self.client.force_authenticate(user=self.admin)
        
        # Admin should be able to access any profile
        url = f"{reverse('v1:userprofile')}?user_id={self.user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class RoleBasedPermissionTestCase(BasePermissionTestCase):
    """Test suite for role-based permissions."""

    def test_role_based_access(self):
        """Test access based on user roles."""
        # Test manager access
        self.client.force_authenticate(user=self.manager)
        manager_urls = [
            reverse('v1:reports'),
            reverse('v1:team-management')
        ]
        
        for url in manager_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test regular user access denied
        self.client.force_authenticate(user=self.user)
        for url in manager_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_inheritance(self):
        """Test role permission inheritance."""
        # Admin should have all permissions
        self.client.force_authenticate(user=self.admin)
        all_urls = [
            reverse('v1:reports'),
            reverse('v1:team-management'),
            reverse('v1:user-dashboard')
        ]
        
        for url in all_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multiple_roles(self):
        """Test user with multiple roles."""
        # Give manager an additional role
        self.manager.roles.add(self.user_role)
        self.client.force_authenticate(user=self.manager)
        
        # Should have access to both manager and user endpoints
        urls = [
            reverse('v1:reports'),  # Manager endpoint
            reverse('v1:user-dashboard')  # User endpoint
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

class VerifiedUserPermissionTestCase(BasePermissionTestCase):
    """Test suite for verified user permissions."""

    def test_verified_user_access(self):
        """Test access for verified users."""
        self.user.is_verified = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        
        url = reverse('v1:verified-only')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unverified_user_access_denied(self):
        """Test access denied for unverified users."""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('v1:verified-only')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class ReadOnlyPermissionTestCase(BasePermissionTestCase):
    """Test suite for read-only permissions."""

    def test_read_only_access(self):
        """Test read-only access to endpoints."""
        self.client.force_authenticate(user=self.user)
        url = reverse('v1:public-data')
        
        # GET should be allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # POST should be denied
        response = self.client.post(url, {'data': 'test'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # PUT should be denied
        response = self.client.put(url, {'data': 'test'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # DELETE should be denied
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class ObjectLevelPermissionTestCase(BasePermissionTestCase):
    """Test suite for object-level permissions."""

    def setUp(self):
        """Set up additional test data."""
        super().setUp()
        self.team = Team.objects.create(
            name='Test Team',
            leader=self.manager
        )
        self.team.members.add(self.user)

    def test_team_leader_permissions(self):
        """Test team leader permissions on team objects."""
        self.client.force_authenticate(user=self.manager)
        url = f"{reverse('v1:teams')}{self.team.id}/"
        
        # Leader should have full access
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.patch(url, {'name': 'Updated Team'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_team_member_permissions(self):
        """Test team member permissions on team objects."""
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('v1:teams')}{self.team.id}/"
        
        # Member should have read access only
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.patch(url, {'name': 'Updated Team'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_access_denied(self):
        """Test non-member access to team objects."""
        non_member = User.objects.create_user(
            username='nonmember',
            email='nonmember@example.com',
            password='NonMemberPass123!'
        )
        self.client.force_authenticate(user=non_member)
        
        url = f"{reverse('v1:teams')}{self.team.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 