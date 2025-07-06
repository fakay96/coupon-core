"""
Category Preference Management Service

This service provides robust functionality for managing user category preferences,
including initialization, updates, and validation.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from geodiscounts.models import Category, UserPreference, Conversation

User = get_user_model()
logger = logging.getLogger(__name__)


class CategoryPreferenceService:
    """
    Service for managing user category preferences.
    
    Provides methods for:
    - Getting user category preferences
    - Updating category preferences
    - Validating category preferences
    - Bulk operations on preferences
    """
    
    @staticmethod
    def get_user_category_preferences(user: User) -> Dict[str, Any]:
        """
        Get all category preferences for a user.
        
        Args:
            user: The user whose preferences to retrieve
            
        Returns:
            Dictionary containing category preferences with structure:
            {
                'categories': [
                    {
                        'id': category_id,
                        'name': category_name,
                        'confidence': confidence_score,
                        'is_selected': boolean
                    }
                ],
                'selected_categories': [category_names],
                'unselected_categories': [category_names]
            }
        """
        try:
            # Get all categories
            all_categories = Category.objects.all().order_by('name')
            
            # Get user preferences
            user_preferences = UserPreference.objects.filter(
                user=user,
                preference_type=UserPreference.PreferenceType.CATEGORY,
                key='category_preference'
            )
            
            # Create a mapping of category names to preferences
            preference_map = {
                pref.value: pref for pref in user_preferences
            }
            
            # Build response structure
            categories = []
            selected_categories = []
            unselected_categories = []
            
            for category in all_categories:
                preference = preference_map.get(category.name)
                confidence = preference.confidence if preference else 0.0
                is_selected = confidence > 0.3  # Threshold for selection
                
                category_data = {
                    'id': category.id,
                    'name': category.name,
                    'confidence': confidence,
                    'is_selected': is_selected,
                    'image': category.image.url if category.image else None
                }
                categories.append(category_data)
                
                if is_selected:
                    selected_categories.append(category.name)
                else:
                    unselected_categories.append(category.name)
            
            return {
                'categories': categories,
                'selected_categories': selected_categories,
                'unselected_categories': unselected_categories,
                'total_categories': len(categories),
                'selected_count': len(selected_categories),
                'unselected_count': len(unselected_categories)
            }
            
        except Exception as e:
            logger.error(f"Error getting category preferences for user {user.username}: {e}")
            return {
                'categories': [],
                'selected_categories': [],
                'unselected_categories': [],
                'total_categories': 0,
                'selected_count': 0,
                'unselected_count': 0,
                'error': str(e)
            }
    
    @staticmethod
    def update_category_preferences(
        user: User, 
        category_updates: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update category preferences for a user.
        
        Args:
            user: The user whose preferences to update
            category_updates: List of category updates with structure:
                [
                    {
                        'category_name': str,
                        'is_selected': bool,
                        'confidence': float (optional)
                    }
                ]
                
        Returns:
            Tuple of (success: bool, result: Dict)
        """
        try:
            with transaction.atomic():
                # Get or create default conversation
                conversation, _ = Conversation.objects.get_or_create(
                    user=user,
                    defaults={
                        'title': 'Category Preference Update',
                        'status': 'active'
                    }
                )
                
                updated_count = 0
                errors = []
                
                for update in category_updates:
                    try:
                        category_name = update.get('category_name')
                        is_selected = update.get('is_selected', True)
                        confidence = update.get('confidence', 0.8 if is_selected else 0.1)
                        
                        # Validate inputs
                        if not category_name:
                            errors.append("Category name is required")
                            continue
                        
                        if not isinstance(is_selected, bool):
                            errors.append(f"is_selected must be boolean for {category_name}")
                            continue
                        
                        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                            errors.append(f"Confidence must be between 0 and 1 for {category_name}")
                            continue
                        
                        # Check if category exists
                        try:
                            category = Category.objects.get(name=category_name)
                        except Category.DoesNotExist:
                            errors.append(f"Category '{category_name}' does not exist")
                            continue
                        
                        # Update or create preference
                        preference, created = UserPreference.objects.get_or_create(
                            user=user,
                            preference_type=UserPreference.PreferenceType.CATEGORY,
                            key='category_preference',
                            value=category_name,
                            defaults={
                                'conversation': conversation,
                                'confidence': confidence
                            }
                        )
                        
                        if not created:
                            preference.confidence = confidence
                            preference.save(update_fields=['confidence', 'updated_at'])
                        
                        updated_count += 1
                        
                    except Exception as e:
                        error_msg = f"Error updating preference for {update.get('category_name', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                if errors:
                    return False, {
                        'success': False,
                        'updated_count': updated_count,
                        'errors': errors,
                        'message': f"Updated {updated_count} preferences with {len(errors)} errors"
                    }
                
                return True, {
                    'success': True,
                    'updated_count': updated_count,
                    'message': f"Successfully updated {updated_count} category preferences"
                }
                
        except Exception as e:
            logger.error(f"Error updating category preferences for user {user.username}: {e}")
            return False, {
                'success': False,
                'error': str(e),
                'message': 'Failed to update category preferences'
            }
    
    @staticmethod
    def bulk_update_category_preferences(
        user: User,
        selected_categories: List[str],
        unselected_categories: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Bulk update category preferences by providing lists of selected/unselected categories.
        
        Args:
            user: The user whose preferences to update
            selected_categories: List of category names to mark as selected
            unselected_categories: List of category names to mark as unselected (optional)
            
        Returns:
            Tuple of (success: bool, result: Dict)
        """
        try:
            # Validate inputs
            if not isinstance(selected_categories, list):
                return False, {
                    'success': False,
                    'error': 'selected_categories must be a list'
                }
            
            if unselected_categories is not None and not isinstance(unselected_categories, list):
                return False, {
                    'success': False,
                    'error': 'unselected_categories must be a list'
                }
            
            # Check for duplicates
            if unselected_categories:
                duplicates = set(selected_categories) & set(unselected_categories)
                if duplicates:
                    return False, {
                        'success': False,
                        'error': f'Categories cannot be both selected and unselected: {duplicates}'
                    }
            
            # Build updates list
            updates = []
            
            # Add selected categories
            for category_name in selected_categories:
                updates.append({
                    'category_name': category_name,
                    'is_selected': True,
                    'confidence': 0.8
                })
            
            # Add unselected categories
            if unselected_categories:
                for category_name in unselected_categories:
                    updates.append({
                        'category_name': category_name,
                        'is_selected': False,
                        'confidence': 0.1
                    })
            
            return CategoryPreferenceService.update_category_preferences(user, updates)
            
        except Exception as e:
            logger.error(f"Error in bulk update for user {user.username}: {e}")
            return False, {
                'success': False,
                'error': str(e),
                'message': 'Failed to perform bulk update'
            }
    
    @staticmethod
    def toggle_category_preference(
        user: User,
        category_name: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Toggle a single category preference.
        
        Args:
            user: The user whose preference to toggle
            category_name: Name of the category to toggle
            
        Returns:
            Tuple of (success: bool, result: Dict)
        """
        try:
            # Get current preference
            try:
                preference = UserPreference.objects.get(
                    user=user,
                    preference_type=UserPreference.PreferenceType.CATEGORY,
                    key='category_preference',
                    value=category_name
                )
                current_confidence = preference.confidence
                is_currently_selected = current_confidence > 0.3
                
                # Toggle
                new_confidence = 0.1 if is_currently_selected else 0.8
                preference.confidence = new_confidence
                preference.save(update_fields=['confidence', 'updated_at'])
                
                return True, {
                    'success': True,
                    'category_name': category_name,
                    'was_selected': is_currently_selected,
                    'is_now_selected': not is_currently_selected,
                    'new_confidence': new_confidence,
                    'message': f"Category '{category_name}' {'deselected' if is_currently_selected else 'selected'}"
                }
                
            except UserPreference.DoesNotExist:
                # Create new preference as selected
                conversation, _ = Conversation.objects.get_or_create(
                    user=user,
                    defaults={
                        'title': 'Category Preference Toggle',
                        'status': 'active'
                    }
                )
                
                UserPreference.objects.create(
                    user=user,
                    conversation=conversation,
                    preference_type=UserPreference.PreferenceType.CATEGORY,
                    key='category_preference',
                    value=category_name,
                    confidence=0.8
                )
                
                return True, {
                    'success': True,
                    'category_name': category_name,
                    'was_selected': False,
                    'is_now_selected': True,
                    'new_confidence': 0.8,
                    'message': f"Category '{category_name}' selected"
                }
                
        except Exception as e:
            logger.error(f"Error toggling category preference for user {user.username}, category {category_name}: {e}")
            return False, {
                'success': False,
                'error': str(e),
                'message': f'Failed to toggle category preference for {category_name}'
            }
    
    @staticmethod
    def validate_category_names(category_names: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that all category names exist in the database.
        
        Args:
            category_names: List of category names to validate
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        for category_name in category_names:
            if not Category.objects.filter(name=category_name).exists():
                errors.append(f"Category '{category_name}' does not exist")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_available_categories() -> List[Dict[str, Any]]:
        """
        Get all available categories for reference.
        
        Returns:
            List of category dictionaries
        """
        try:
            categories = Category.objects.all().order_by('name')
            return [
                {
                    'id': category.id,
                    'name': category.name,
                    'image': category.image.url if category.image else None,
                    'created_at': category.created_at,
                    'updated_at': category.updated_at
                }
                for category in categories
            ]
        except Exception as e:
            logger.error(f"Error getting available categories: {e}")
            return [] 