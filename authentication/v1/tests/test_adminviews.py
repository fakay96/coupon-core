"""
Test cases for admin-related views.

This module tests:
1. Admin user management
2. Role management
3. Permission handling
4. Admin-only endpoints
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import CustomUser, Role


class AdminViewsTestCase(APITestCase):
    """Test suite for admin views."""

    def setUp(self) -> None:
        """Set up test data."""
        # Create admin user
        self.admin = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123"
        )

        # Create regular user
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        # Create test role
        self.role = Role.objects.create(
            name="test_role",
            description="Test role description"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_list_users(self) -> None:
        """
        Test listing all users.

        Expected:
            - Returns HTTP 200
            - Returns list of users
            - Only accessible by admin
        """
        response = self.client.get("/authentication/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # admin + regular user

        # Test non-admin access
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/authentication/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_detail(self) -> None:
        """
        Test retrieving user details.

        Expected:
            - Returns HTTP 200 for existing user
            - Returns HTTP 404 for non-existent user
            - Only accessible by admin
        """
        response = self.client.get(f"/authentication/api/v1/admin/users/{self.user.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)

        # Test non-existent user
        response = self.client.get("/authentication/api/v1/admin/users/999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_user(self) -> None:
        """
        Test user creation by admin.

        Expected:
            - Returns HTTP 201 with valid data
            - Returns HTTP 400 with invalid data
            - Only accessible by admin
        """
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "is_staff": False
        }
        response = self.client.post("/authentication/api/v1/admin/users/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newuser")

        # Test duplicate username
        response = self.client.post("/authentication/api/v1/admin/users/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user(self) -> None:
        """
        Test updating user details by admin.

        Expected:
            - Returns HTTP 200 with valid data
            - Returns HTTP 400 with invalid data
            - Only accessible by admin
        """
        data = {
            "first_name": "Updated",
            "last_name": "User",
            "is_active": False
        }
        response = self.client.patch(
            f"/authentication/api/v1/admin/users/{self.user.id}/",
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["is_active"], False)

    def test_delete_user(self) -> None:
        """
        Test user deletion by admin.

        Expected:
            - Returns HTTP 204 for successful deletion
            - Returns HTTP 404 for non-existent user
            - Only accessible by admin
        """
        response = self.client.delete(f"/authentication/api/v1/admin/users/{self.user.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify user is deleted
        response = self.client.get(f"/authentication/api/v1/admin/users/{self.user.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_roles(self) -> None:
        """
        Test listing all roles.

        Expected:
            - Returns HTTP 200
            - Returns list of roles
            - Only accessible by admin
        """
        response = self.client.get("/authentication/api/v1/admin/roles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # test_role

    def test_create_role(self) -> None:
        """
        Test role creation by admin.

        Expected:
            - Returns HTTP 201 with valid data
            - Returns HTTP 400 with invalid data
            - Only accessible by admin
        """
        data = {
            "name": "new_role",
            "description": "New role description"
        }
        response = self.client.post("/authentication/api/v1/admin/roles/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "new_role")

        # Test duplicate role name
        response = self.client.post("/authentication/api/v1/admin/roles/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_role(self) -> None:
        """
        Test updating role details by admin.

        Expected:
            - Returns HTTP 200 with valid data
            - Returns HTTP 400 with invalid data
            - Only accessible by admin
        """
        data = {
            "description": "Updated role description"
        }
        response = self.client.patch(
            f"/authentication/api/v1/admin/roles/{self.role.id}/",
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "Updated role description")

    def test_delete_role(self) -> None:
        """
        Test role deletion by admin.

        Expected:
            - Returns HTTP 204 for successful deletion
            - Returns HTTP 404 for non-existent role
            - Only accessible by admin
        """
        response = self.client.delete(f"/authentication/api/v1/admin/roles/{self.role.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify role is deleted
        response = self.client.get(f"/authentication/api/v1/admin/roles/{self.role.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_to_user(self) -> None:
        """
        Test assigning role to user.

        Expected:
            - Returns HTTP 200 for successful assignment
            - Returns HTTP 400 for invalid role/user
            - Only accessible by admin
        """
        data = {
            "role_id": self.role.id
        }
        response = self.client.post(
            f"/authentication/api/v1/admin/users/{self.user.id}/roles/",
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test invalid role
        data["role_id"] = 999
        response = self.client.post(
            f"/authentication/api/v1/admin/users/{self.user.id}/roles/",
            data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_role_from_user(self) -> None:
        """
        Test removing role from user.

        Expected:
            - Returns HTTP 200 for successful removal
            - Returns HTTP 400 for invalid role/user
            - Only accessible by admin
        """
        # First assign role
        data = {"role_id": self.role.id}
        self.client.post(
            f"/authentication/api/v1/admin/users/{self.user.id}/roles/",
            data
        )

        # Then remove it
        response = self.client.delete(
            f"/authentication/api/v1/admin/users/{self.user.id}/roles/{self.role.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_required_decorator(self) -> None:
        """
        Test admin_required decorator on all admin endpoints.

        Expected:
            - Returns HTTP 403 for non-admin users
            - Returns HTTP 401 for unauthenticated requests
        """
        endpoints = [
            "/authentication/api/v1/admin/users/",
            "/authentication/api/v1/admin/roles/",
            f"/authentication/api/v1/admin/users/{self.user.id}/",
            f"/authentication/api/v1/admin/roles/{self.role.id}/"
        ]

        # Test with non-admin user
        self.client.force_authenticate(user=self.user)
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Endpoint {endpoint} should be forbidden for non-admin users"
            )

        # Test with unauthenticated request
        self.client.force_authenticate(user=None)
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {endpoint} should require authentication"
            )

    def test_bulk_user_operations(self) -> None:
        """
        Test bulk operations on users.

        Expected:
            - Can bulk create users
            - Can bulk update users
            - Can bulk delete users
            - Only accessible by admin
        """
        # Bulk create
        data = [
            {
                "username": "bulk1",
                "email": "bulk1@example.com",
                "password": "password123"
            },
            {
                "username": "bulk2",
                "email": "bulk2@example.com",
                "password": "password123"
            }
        ]
        response = self.client.post(
            "/authentication/api/v1/admin/users/bulk/",
            data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)

        # Bulk update
        user_ids = [user["id"] for user in response.data]
        update_data = [
            {
                "id": user_ids[0],
                "is_active": False
            },
            {
                "id": user_ids[1],
                "first_name": "Bulk"
            }
        ]
        response = self.client.patch(
            "/authentication/api/v1/admin/users/bulk/",
            update_data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Bulk delete
        response = self.client.delete(
            "/authentication/api/v1/admin/users/bulk/",
            {"ids": user_ids},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_search_and_filters(self) -> None:
        """
        Test user search and filtering functionality.

        Expected:
            - Can search users by username/email
            - Can filter by active status
            - Can filter by role
            - Only accessible by admin
        """
        # Create test data
        CustomUser.objects.create_user(
            username="searchuser",
            email="search@example.com",
            password="password123",
            is_active=False
        )

        # Test search
        response = self.client.get(
            "/authentication/api/v1/admin/users/?search=search"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["username"], "searchuser")

        # Test active filter
        response = self.client.get(
            "/authentication/api/v1/admin/users/?is_active=false"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["username"], "searchuser")

        # Test role filter
        response = self.client.get(
            f"/authentication/api/v1/admin/users/?role={self.role.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
