"""
Django Admin Configuration for the Discount Discovery System.

This module configures the Django Admin panel for managing:
- **Categories**: Discount categories with image previews (supports SVG, PNG, JPEG).
- **Retailers**: Businesses that offer location-based discounts.
- **Discounts**: Individual discount offers linked to retailers and categories.
- **Shared Discounts**: Group discounts that multiple users can share.

### Key Features:
- **Image Preview Handling**:
  - Supports **SVG images** using `<object>` for proper rendering.
  - Uses `<img>` for PNG/JPEG to maintain correct preview behavior.
- **Admin Panel Optimizations**:
  - **Searchable fields** for easy filtering.
  - **List filters** for quick navigation.
  - **Custom ordering** based on creation timestamps.

Author: Your Name
Date: YYYY-MM-DD
"""

from django.contrib import admin
from django.utils.html import format_html
import os

from .models import Category, Retailer, Discount, SharedDiscount, WebSocketDiscountRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Category model.

    This panel allows management of discount categories, including:
    - Viewing and filtering categories.
    - Uploading category images (supports SVG, PNG, JPEG).
    - Displaying an image preview in the admin panel.
    """

    list_display: tuple[str, ...] = ("name", "image_preview", "created_at", "updated_at")
    search_fields: tuple[str, ...] = ("name",)
    ordering: tuple[str, ...] = ("created_at",)

    def image_preview(self, obj: Category) -> str:
        """
        Displays a preview of the category image in the admin panel.

        - Uses `<object>` for SVG previews.
        - Uses `<img>` for PNG/JPEG previews.

        Args:
            obj (Category): The category object with an associated image.

        Returns:
            str: An HTML formatted image or object tag.
        """
        if obj.image:
            file_extension = os.path.splitext(obj.image.url)[-1].lower()
            if file_extension == ".svg":
                return format_html(
                    '<object data="{}" type="image/svg+xml" width="50" height="50"></object>',
                    obj.image.url
                )
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:5px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Retailer model.

    Allows management of businesses offering discounts. Supports:
    - Searching by retailer name and contact info.
    - Viewing retailer locations on a map (if enabled).
    - Sorting by creation date.

    Prevents reverse relation lookups to avoid cross-shard joins.
    """

    list_display: tuple[str, ...] = ("name", "contact_info", "location", "created_at", "updated_at")
    search_fields: tuple[str, ...] = ("name", "contact_info")
    ordering: tuple[str, ...] = ("created_at",)

    def get_queryset(self, request):
        """
        Prevent automatic JOINs that could span multiple databases.

        Args:
            request: Admin request object.

        Returns:
            QuerySet: Unoptimized queryset without select_related().
        """
        return super().get_queryset(request).select_related(None)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Discount model.

    Enables management of retailer discount offers, including:
    - Filtering discounts by category or expiration date.
    - Searching for discounts by retailer, description, or discount code.
    - Displaying an image preview of discount images (supports SVG).
    """

    list_display: tuple[str, ...] = (
        "retailer", "category", "description_preview", "discount_code",
        "expiration_date", "image_preview", "created_at", "updated_at"
    )
    list_filter: tuple[str, ...] = ("category", "expiration_date")
    search_fields: tuple[str, ...] = ("retailer__name", "description", "discount_code")
    ordering: tuple[str, ...] = ("-created_at",)

    def description_preview(self, obj: Discount) -> str:
        """
        Displays a shortened preview of the discount description.

        Args:
            obj (Discount): The discount object.

        Returns:
            str: A shortened version of the description (max 50 characters).
        """
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description

    description_preview.short_description = "Description"

    def image_preview(self, obj: Discount) -> str:
        """
        Displays a preview of the discount image in the admin panel.

        - Uses `<object>` for SVG previews.
        - Uses `<img>` for PNG/JPEG previews.

        Args:
            obj (Discount): The discount object with an associated image.

        Returns:
            str: An HTML formatted image or object tag.
        """
        if obj.image:
            file_extension = os.path.splitext(obj.image.url)[-1].lower()
            if file_extension == ".svg":
                return format_html(
                    '<object data="{}" type="image/svg+xml" width="50" height="50"></object>',
                    obj.image.url
                )
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:5px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(SharedDiscount)
class SharedDiscountAdmin(admin.ModelAdmin):
    """
    Admin configuration for the SharedDiscount model.

    This panel enables management of shared discount codes, including:
    - Filtering by discount status (active, completed, expired).
    - Searching for shared discounts by group name or discount code.
    - Sorting by creation date.
    """

    list_display: tuple[str, ...] = ("discount", "group_name", "status", "created_at", "updated_at")
    list_filter: tuple[str, ...] = ("status",)
    search_fields: tuple[str, ...] = ("group_name", "discount__discount_code")
    ordering: tuple[str, ...] = ("-created_at",)

@admin.register(WebSocketDiscountRequest)
class WebSocketDiscountRequestAdmin(admin.ModelAdmin):
    """
    Admin configuration for the WebSocketDiscountRequest model.
    
    Provides an interface for managing real-time discount requests through WebSocket connections.
    """
    
    list_display = (
        'request_id',
        'user_id',
        'user_email',
        'location_display',
        'radius',
        'status',
        'created_at',
        'updated_at'
    )
    
    list_filter = (
        'status',
        'created_at',
        'updated_at'
    )
    
    search_fields = (
        'request_id',
        'user_id',
        'user_email',
        'location',
        'radius'
    )
    
    readonly_fields = (
        'request_id',
        'created_at',
        'updated_at',
        'location_display',
        'conversation_history_display'
    )
    
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'request_id',
                'user_id',
                'user_email',
                'radius',
                'status',
                'websocket_url'
            )
        }),
        ('Location', {
            'fields': (
                'location',
                'location_display'
            )
        }),
        ('Results', {
            'fields': (
                'results',
                'conversation_history_display'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def location_display(self, obj: WebSocketDiscountRequest) -> str:
        """Display the location coordinates in a readable format."""
        if obj.location:
            return f"Lat: {obj.location.y:.6f}, Lon: {obj.location.x:.6f}"
        return "No location"
    location_display.short_description = "Location Coordinates"
    
    def conversation_history_display(self, obj: WebSocketDiscountRequest) -> str:
        """Display the conversation history in a readable format."""
        if not obj.conversation_history:
            return "No conversation history"
        
        formatted_history = []
        for msg in obj.conversation_history:
            timestamp = msg.get('timestamp', '')
            role = msg.get('role', '')
            content = msg.get('content', '')
            formatted_history.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(formatted_history)
    conversation_history_display.short_description = "Conversation History"
    