"""
Views for managing user category preferences.

This module provides endpoints for:
- Getting user category preferences
- Updating category preferences
- Toggling individual category preferences
- Bulk operations on preferences
"""

import logging
from typing import Any, Dict, List

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from authentication.v1.services.category_preference_service import CategoryPreferenceService

logger = logging.getLogger(__name__)


class CategoryPreferenceView(APIView):
    """
    View for managing user category preferences.
    
    Provides endpoints for getting and updating category preferences.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="""
        Get all category preferences for the authenticated user.
        
        This endpoint returns comprehensive information about the user's category preferences for discount discovery.
        It includes both individual category details and summary statistics to help understand user preferences.
        
        **Category Preference System:**
        - Each category has a confidence score (0.0 to 1.0) indicating AI's confidence in user preference
        - Categories with confidence >= 0.5 are considered "selected"
        - Categories with confidence < 0.5 are considered "unselected"
        - Confidence scores are used for personalized discount recommendations
        
        **Available Categories:**
        - fashion: Clothing, shoes, accessories, jewelry
        - grocery: Food, beverages, household items, cleaning supplies
        - electronics: Tech gadgets, appliances, computers, phones
        - home: Furniture, decor, garden, DIY supplies
        - beauty: Cosmetics, personal care, skincare, haircare
        - sports: Athletic equipment, outdoor gear, fitness items
        
        **Response Structure:**
        - Individual category details with confidence scores
        - Summary lists of selected/unselected categories
        - Total counts for easy UI implementation
        """,
        responses={
            200: openapi.Response(
                description="Successfully retrieved category preferences",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="Detailed information for each available category",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, example="fashion"),
                                    'confidence': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.85),
                                    'is_selected': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                                    'image': openapi.Schema(type=openapi.TYPE_STRING, example="https://example.com/images/fashion.jpg", nullable=True),
                                }
                            )
                        ),
                        'selected_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of category names that are currently selected (confidence >= 0.5)",
                            example=["fashion", "grocery", "electronics"]
                        ),
                        'unselected_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of category names that are currently unselected (confidence < 0.5)",
                            example=["sports", "beauty", "home"]
                        ),
                        'total_categories': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Total number of available categories",
                            example=6
                        ),
                        'selected_count': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Number of selected categories",
                            example=3
                        ),
                        'unselected_count': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Number of unselected categories",
                            example=3
                        ),
                        'preference_summary': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Summary statistics about user preferences",
                            properties={
                                'most_confident_category': openapi.Schema(type=openapi.TYPE_STRING, example="grocery"),
                                'highest_confidence_score': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.92),
                                'least_confident_category': openapi.Schema(type=openapi.TYPE_STRING, example="sports"),
                                'lowest_confidence_score': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.15),
                                'average_confidence': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.58)
                            }
                        )
                    }
                )
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Authentication error message",
                            example="Authentication credentials were not provided"
                        )
                    }
                )
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Generic error message",
                            example="Internal server error"
                        ),
                        'details': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Technical error details for debugging",
                            example="Failed to retrieve category preferences"
                        )
                    }
                )
            ),
        }
    )
    def get(self, request: Any) -> Response:
        """
        Get all category preferences for the authenticated user.
        
        Returns:
            Response with category preferences data
        """
        try:
            preferences = CategoryPreferenceService.get_user_category_preferences(request.user)
            
            if 'error' in preferences:
                return Response(
                    {'error': preferences['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(preferences, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting category preferences for user {request.user.username}: {e}")
            return Response(
                {'error': 'Failed to retrieve category preferences'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_description="""
        Update category preferences for the authenticated user.
        
        This endpoint allows users to update their category preferences for personalized discount discovery.
        You can update preferences in two ways:
        
        **Method 1: Individual Updates**
        Use `category_updates` array to update specific categories with new confidence scores.
        
        **Method 2: Bulk Updates**
        Use `selected_categories` and `unselected_categories` arrays to set preferences in bulk.
        Categories in `selected_categories` get confidence score 0.8, others get 0.2.
        
        **Confidence Score System:**
        - 0.0-0.4: Strongly unselected (user explicitly doesn't want this category)
        - 0.5-0.6: Neutral (user hasn't expressed preference)
        - 0.7-1.0: Selected (user is interested in this category)
        
        **Validation Rules:**
        - Category names must exist in the system
        - Confidence scores must be between 0.0 and 1.0
        - At least one update method must be provided
        
        **Response:**
        - Returns success status and count of updated categories
        - Lists any validation errors that occurred
        - Provides summary of changes made
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_updates': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Array of individual category updates with confidence scores",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'category_name': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Name of the category to update",
                                example="fashion"
                            ),
                            'is_selected': openapi.Schema(
                                type=openapi.TYPE_BOOLEAN,
                                description="Whether the category should be selected",
                                example=True
                            ),
                            'confidence': openapi.Schema(
                                type=openapi.TYPE_NUMBER,
                                description="Confidence score between 0.0 and 1.0. If not provided, defaults to 0.8 for selected, 0.2 for unselected",
                                example=0.85,
                                minimum=0.0,
                                maximum=1.0
                            ),
                        },
                        required=['category_name', 'is_selected']
                    ),
                    example=[
                        {"category_name": "fashion", "is_selected": True, "confidence": 0.9},
                        {"category_name": "sports", "is_selected": False, "confidence": 0.1}
                    ]
                ),
                'selected_categories': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="Array of category names to mark as selected (confidence = 0.8)",
                    example=["fashion", "grocery", "electronics"]
                ),
                'unselected_categories': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="Array of category names to mark as unselected (confidence = 0.2)",
                    example=["sports", "beauty", "home"]
                ),
            },
            example={
                "category_updates": [
                    {"category_name": "fashion", "is_selected": True, "confidence": 0.9},
                    {"category_name": "grocery", "is_selected": True, "confidence": 0.8}
                ]
            }
        ),
        responses={
            200: openapi.Response(
                description="Successfully updated category preferences",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(
                            type=openapi.TYPE_BOOLEAN,
                            description="Whether the update operation was successful",
                            example=True
                        ),
                        'updated_count': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Number of categories that were successfully updated",
                            example=3
                        ),
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Success message describing the operation",
                            example="Successfully updated 3 category preferences"
                        ),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of validation errors that occurred (if any)",
                            example=["Category 'invalid_category' does not exist"],
                            nullable=True
                        ),
                        'updated_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'category_name': openapi.Schema(type=openapi.TYPE_STRING, example="fashion"),
                                    'old_confidence': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.5),
                                    'new_confidence': openapi.Schema(type=openapi.TYPE_NUMBER, example=0.9),
                                    'was_selected': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                    'is_now_selected': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True)
                                }
                            ),
                            description="Details of each category that was updated",
                            example=[
                                {
                                    "category_name": "fashion",
                                    "old_confidence": 0.5,
                                    "new_confidence": 0.9,
                                    "was_selected": False,
                                    "is_now_selected": True
                                }
                            ]
                        ),
                        'summary': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Summary of the update operation",
                            properties={
                                'total_categories': openapi.Schema(type=openapi.TYPE_INTEGER, example=6),
                                'selected_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=3),
                                'unselected_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=3),
                                'method_used': openapi.Schema(type=openapi.TYPE_STRING, example="individual_updates")
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request - validation errors",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Error message describing the issue",
                            example="Invalid request format"
                        ),
                        'details': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Additional error details",
                            example="Must provide either category_updates or selected_categories/unselected_categories"
                        ),
                        'validation_errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of specific validation errors",
                            example=[
                                "Category 'invalid_category' does not exist",
                                "Confidence score must be between 0.0 and 1.0"
                            ]
                        ),
                        'available_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of valid category names",
                            example=["fashion", "grocery", "electronics", "home", "beauty", "sports"]
                        )
                    }
                )
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Authentication error message",
                            example="Authentication credentials were not provided"
                        )
                    }
                )
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Generic error message",
                            example="Internal server error"
                        ),
                        'details': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Technical error details for debugging",
                            example="Failed to update category preferences"
                        )
                    }
                )
            ),
        }
    )
    def put(self, request: Any) -> Response:
        """
        Update category preferences for the authenticated user.
        
        Supports both individual updates and bulk updates.
        """
        try:
            data = request.data
            
            # Handle bulk update with selected/unselected lists
            if 'selected_categories' in data or 'unselected_categories' in data:
                selected_categories = data.get('selected_categories', [])
                unselected_categories = data.get('unselected_categories', [])
                
                success, result = CategoryPreferenceService.bulk_update_category_preferences(
                    request.user,
                    selected_categories,
                    unselected_categories
                )
                
                if success:
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            # Handle individual updates
            elif 'category_updates' in data:
                category_updates = data.get('category_updates', [])
                
                if not isinstance(category_updates, list):
                    return Response(
                        {'error': 'category_updates must be a list'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                success, result = CategoryPreferenceService.update_category_preferences(
                    request.user,
                    category_updates
                )
                
                if success:
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                return Response(
                    {'error': 'Must provide either category_updates or selected_categories/unselected_categories'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error updating category preferences for user {request.user.username}: {e}")
            return Response(
                {'error': 'Failed to update category preferences'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryPreferenceToggleView(APIView):
    """
    View for toggling individual category preferences.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Toggle a single category preference",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the category to toggle"
                ),
            },
            required=['category_name']
        ),
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'category_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'was_selected': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'is_now_selected': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'new_confidence': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description="Bad request - invalid category name"),
            500: openapi.Response(description="Internal server error"),
        }
    )
    def post(self, request: Any) -> Response:
        """
        Toggle a single category preference.
        
        If the category is currently selected, it will be deselected.
        If the category is currently unselected, it will be selected.
        """
        try:
            category_name = request.data.get('category_name')
            
            if not category_name:
                return Response(
                    {'error': 'category_name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success, result = CategoryPreferenceService.toggle_category_preference(
                request.user,
                category_name
            )
            
            if success:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error toggling category preference for user {request.user.username}: {e}")
            return Response(
                {'error': 'Failed to toggle category preference'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableCategoriesView(APIView):
    """
    View for getting all available categories.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get all available categories",
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'image': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            ),
            500: openapi.Response(description="Internal server error"),
        }
    )
    def get(self, request: Any) -> Response:
        """
        Get all available categories.
        
        Returns:
            Response with list of all available categories
        """
        try:
            categories = CategoryPreferenceService.get_available_categories()
            return Response(categories, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting available categories: {e}")
            return Response(
                {'error': 'Failed to retrieve available categories'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryPreferenceValidationView(APIView):
    """
    View for validating category names.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Validate category names",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_names': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="List of category names to validate"
                ),
            },
            required=['category_names']
        ),
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING)
                        ),
                        'valid_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING)
                        ),
                        'invalid_categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING)
                        ),
                    }
                )
            ),
            400: openapi.Response(description="Bad request - invalid input"),
            500: openapi.Response(description="Internal server error"),
        }
    )
    def post(self, request: Any) -> Response:
        """
        Validate a list of category names.
        
        Returns:
            Response with validation results
        """
        try:
            category_names = request.data.get('category_names', [])
            
            if not isinstance(category_names, list):
                return Response(
                    {'error': 'category_names must be a list'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            is_valid, errors = CategoryPreferenceService.validate_category_names(category_names)
            
            # Separate valid and invalid categories
            valid_categories = []
            invalid_categories = []
            
            for category_name in category_names:
                if any(error.endswith(f"'{category_name}' does not exist") for error in errors):
                    invalid_categories.append(category_name)
                else:
                    valid_categories.append(category_name)
            
            return Response({
                'is_valid': is_valid,
                'errors': errors,
                'valid_categories': valid_categories,
                'invalid_categories': invalid_categories,
                'total_categories': len(category_names),
                'valid_count': len(valid_categories),
                'invalid_count': len(invalid_categories),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error validating category names: {e}")
            return Response(
                {'error': 'Failed to validate category names'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 