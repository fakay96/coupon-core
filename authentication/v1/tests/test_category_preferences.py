"""
Tests for category preference functionality.

This module tests:
- CategoryPreferenceService methods
- Category preference views
- Signal for initializing category preferences
- Integration with user profile updates
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

from authentication.models import UserProfile
from authentication.v1.services.category_preference_service import CategoryPreferenceService
from authentication.v1.views.category_preference_views import (
    CategoryPreferenceView,
    CategoryPreferenceToggleView,
    AvailableCategoriesView,
    CategoryPreferenceValidationView
)

User = get_user_model()


class CategoryPreferenceServiceTestCase(TestCase):
    """Test cases for CategoryPreferenceService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Mock categories
        self.categories = [
            {'id': 1, 'name': 'Food', 'image': None},
            {'id': 2, 'name': 'Shopping', 'image': None},
            {'id': 3, 'name': 'Entertainment', 'image': None},
        ]

    @patch('authentication.v1.services.category_preference_service.Category')
    @patch('authentication.v1.services.category_preference_service.UserPreference')
    def test_get_user_category_preferences(self, mock_user_preference, mock_category):
        """Test getting user category preferences."""
        # Mock Category.objects.all()
        mock_category.objects.all.return_value = [
            MagicMock(id=1, name='Food', image=None),
            MagicMock(id=2, name='Shopping', image=None),
            MagicMock(id=3, name='Entertainment', image=None),
        ]
        
        # Mock UserPreference.objects.filter()
        mock_pref1 = MagicMock()
        mock_pref1.value = 'Food'
        mock_pref1.confidence = 0.8
        
        mock_pref2 = MagicMock()
        mock_pref2.value = 'Shopping'
        mock_pref2.confidence = 0.2
        
        mock_user_preference.objects.filter.return_value = [mock_pref1, mock_pref2]
        
        result = CategoryPreferenceService.get_user_category_preferences(self.user)
        
        self.assertIn('categories', result)
        self.assertIn('selected_categories', result)
        self.assertIn('unselected_categories', result)
        self.assertEqual(len(result['categories']), 3)
        self.assertIn('Food', result['selected_categories'])
        self.assertIn('Entertainment', result['unselected_categories'])

    @patch('authentication.v1.services.category_preference_service.Category')
    @patch('authentication.v1.services.category_preference_service.UserPreference')
    @patch('authentication.v1.services.category_preference_service.Conversation')
    def test_update_category_preferences(self, mock_conversation, mock_user_preference, mock_category):
        """Test updating category preferences."""
        # Mock conversation
        mock_conv = MagicMock()
        mock_conversation.objects.get_or_create.return_value = (mock_conv, True)
        
        # Mock category exists
        mock_category.objects.get.return_value = MagicMock(name='Food')
        
        # Mock preference creation
        mock_user_preference.objects.get_or_create.return_value = (MagicMock(), True)
        
        updates = [
            {'category_name': 'Food', 'is_selected': True, 'confidence': 0.8},
            {'category_name': 'Shopping', 'is_selected': False, 'confidence': 0.1},
        ]
        
        success, result = CategoryPreferenceService.update_category_preferences(self.user, updates)
        
        self.assertTrue(success)
        self.assertEqual(result['updated_count'], 2)

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_validate_category_names(self, mock_category):
        """Test category name validation."""
        # Mock existing categories
        mock_category.objects.filter.return_value.exists.side_effect = lambda: True
        
        category_names = ['Food', 'Shopping', 'Entertainment']
        is_valid, errors = CategoryPreferenceService.validate_category_names(category_names)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_validate_category_names_invalid(self, mock_category):
        """Test category name validation with invalid names."""
        # Mock some categories don't exist
        def exists_side_effect():
            # First call returns True, second returns False
            exists_side_effect.counter += 1
            return exists_side_effect.counter == 1
        
        exists_side_effect.counter = 0
        mock_category.objects.filter.return_value.exists.side_effect = exists_side_effect
        
        category_names = ['Food', 'InvalidCategory']
        is_valid, errors = CategoryPreferenceService.validate_category_names(category_names)
        
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn('InvalidCategory', errors[0])

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_get_available_categories(self, mock_category):
        """Test getting available categories."""
        # Mock categories
        mock_cat1 = MagicMock(id=1, name='Food', image=None, created_at='2023-01-01', updated_at='2023-01-01')
        mock_cat2 = MagicMock(id=2, name='Shopping', image=None, created_at='2023-01-01', updated_at='2023-01-01')
        
        mock_category.objects.all.return_value.order_by.return_value = [mock_cat1, mock_cat2]
        
        result = CategoryPreferenceService.get_available_categories()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Food')
        self.assertEqual(result[1]['name'], 'Shopping')


class CategoryPreferenceViewsTestCase(APITestCase):
    """Test cases for category preference views."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.get_user_category_preferences')
    def test_get_category_preferences(self, mock_get_preferences):
        """Test getting category preferences."""
        mock_get_preferences.return_value = {
            'categories': [
                {'id': 1, 'name': 'Food', 'confidence': 0.8, 'is_selected': True, 'image': None},
                {'id': 2, 'name': 'Shopping', 'confidence': 0.2, 'is_selected': False, 'image': None},
            ],
            'selected_categories': ['Food'],
            'unselected_categories': ['Shopping'],
            'total_categories': 2,
            'selected_count': 1,
            'unselected_count': 1,
        }
        
        url = reverse('auth:category-preferences')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('categories', response.data)
        self.assertIn('selected_categories', response.data)
        self.assertEqual(len(response.data['categories']), 2)

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.bulk_update_category_preferences')
    def test_update_category_preferences_bulk(self, mock_bulk_update):
        """Test bulk updating category preferences."""
        mock_bulk_update.return_value = (True, {
            'success': True,
            'updated_count': 2,
            'message': 'Successfully updated 2 category preferences'
        })
        
        data = {
            'selected_categories': ['Food', 'Shopping'],
            'unselected_categories': ['Entertainment']
        }
        
        url = reverse('auth:category-preferences')
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.toggle_category_preference')
    def test_toggle_category_preference(self, mock_toggle):
        """Test toggling a category preference."""
        mock_toggle.return_value = (True, {
            'success': True,
            'category_name': 'Food',
            'was_selected': False,
            'is_now_selected': True,
            'new_confidence': 0.8,
            'message': "Category 'Food' selected"
        })
        
        data = {'category_name': 'Food'}
        url = reverse('auth:category-preference-toggle')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['category_name'], 'Food')

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.get_available_categories')
    def test_get_available_categories(self, mock_get_categories):
        """Test getting available categories."""
        mock_get_categories.return_value = [
            {'id': 1, 'name': 'Food', 'image': None, 'created_at': '2023-01-01', 'updated_at': '2023-01-01'},
            {'id': 2, 'name': 'Shopping', 'image': None, 'created_at': '2023-01-01', 'updated_at': '2023-01-01'},
        ]
        
        url = reverse('auth:available-categories')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Food')

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.validate_category_names')
    def test_validate_category_names(self, mock_validate):
        """Test validating category names."""
        mock_validate.return_value = (True, [])
        
        data = {'category_names': ['Food', 'Shopping']}
        url = reverse('auth:category-validation')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_valid'])
        self.assertEqual(len(response.data['errors']), 0)

    def test_validate_category_names_invalid_input(self):
        """Test validating category names with invalid input."""
        data = {'category_names': 'not_a_list'}
        url = reverse('auth:category-validation')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_toggle_category_preference_missing_name(self):
        """Test toggling category preference with missing category name."""
        data = {}
        url = reverse('auth:category-preference-toggle')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_update_category_preferences_invalid_data(self):
        """Test updating category preferences with invalid data."""
        data = {'invalid_field': 'value'}
        url = reverse('auth:category-preferences')
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class CategoryPreferenceSignalTestCase(TestCase):
    """Test cases for category preference initialization signal."""

    @patch('authentication.v1.signals.Category')
    @patch('authentication.v1.signals.UserPreference')
    @patch('authentication.v1.signals.Conversation')
    def test_initialize_category_preferences_signal(self, mock_conversation, mock_user_preference, mock_category):
        """Test that category preferences are initialized when a user is created."""
        # Mock categories exist
        mock_category.objects.all.return_value.exists.return_value = True
        mock_category.objects.all.return_value = [
            MagicMock(name='Food'),
            MagicMock(name='Shopping'),
        ]
        
        # Mock conversation creation
        mock_conv = MagicMock()
        mock_conversation.objects.get_or_create.return_value = (mock_conv, True)
        
        # Mock preference creation
        mock_user_preference.objects.get_or_create.return_value = (MagicMock(), True)
        
        # Create a new user (this should trigger the signal)
        user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        
        # Verify that the signal was called
        mock_conversation.objects.get_or_create.assert_called()
        mock_user_preference.objects.get_or_create.assert_called()

    @patch('authentication.v1.signals.Category')
    def test_initialize_category_preferences_no_categories(self, mock_category):
        """Test signal behavior when no categories exist."""
        # Mock no categories exist
        mock_category.objects.all.return_value.exists.return_value = False
        
        # Create a new user
        user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        
        # Should not raise any exceptions
        self.assertIsNotNone(user)


class CategoryPreferenceIntegrationTestCase(APITestCase):
    """Integration tests for category preferences with user profile."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.bulk_update_category_preferences')
    def test_user_profile_update_with_category_preferences(self, mock_bulk_update):
        """Test updating user profile with category preferences."""
        mock_bulk_update.return_value = (True, {
            'success': True,
            'updated_count': 2,
            'message': 'Successfully updated 2 category preferences'
        })
        
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'selected_categories': ['Food', 'Shopping'],
            'unselected_categories': ['Entertainment']
        }
        
        url = reverse('auth:profile')
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_bulk_update.assert_called_once()

    @patch('authentication.v1.services.category_preference_service.CategoryPreferenceService.get_user_category_preferences')
    def test_user_profile_get_with_category_preferences(self, mock_get_preferences):
        """Test getting user profile with category preferences."""
        mock_get_preferences.return_value = {
            'categories': [
                {'id': 1, 'name': 'Food', 'confidence': 0.8, 'is_selected': True, 'image': None},
            ],
            'selected_categories': ['Food'],
            'unselected_categories': [],
            'total_categories': 1,
            'selected_count': 1,
            'unselected_count': 0,
        }
        
        url = reverse('auth:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('category_preferences', response.data)
        self.assertIn('categories', response.data['category_preferences'])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CategoryPreferenceErrorHandlingTestCase(TestCase):
    """Test cases for error handling in category preferences."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_get_user_category_preferences_error(self, mock_category):
        """Test error handling in get_user_category_preferences."""
        # Mock an exception
        mock_category.objects.all.side_effect = Exception("Database error")
        
        result = CategoryPreferenceService.get_user_category_preferences(self.user)
        
        self.assertIn('error', result)
        self.assertEqual(result['total_categories'], 0)

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_update_category_preferences_error(self, mock_category):
        """Test error handling in update_category_preferences."""
        # Mock an exception
        mock_category.objects.get.side_effect = Exception("Database error")
        
        updates = [{'category_name': 'Food', 'is_selected': True}]
        success, result = CategoryPreferenceService.update_category_preferences(self.user, updates)
        
        self.assertFalse(success)
        self.assertIn('error', result)

    @patch('authentication.v1.services.category_preference_service.Category')
    def test_toggle_category_preference_error(self, mock_category):
        """Test error handling in toggle_category_preference."""
        # Mock an exception
        mock_category.objects.filter.side_effect = Exception("Database error")
        
        success, result = CategoryPreferenceService.toggle_category_preference(self.user, 'Food')
        
        self.assertFalse(success)
        self.assertIn('error', result) 