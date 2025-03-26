"""
Discount Discovery System - Models

This module defines the core database models for the Discount Discovery System.
The system allows retailers to create and share location-based discounts, 
organized into categories.

### Key Features:
- **Retailers**: Businesses offering location-based discounts.
- **Discounts**: Offers that can be redeemed by users.
- **Categories**: Discounts are categorized, and categories have images stored in S3.
- **Shared Discounts**: Enables group discounts where multiple users can share codes.
- **Geospatial Support**: Uses `PointField` for precise location tracking.
- **S3 Integration**: Media files (category images & optional discount images) are stored in DigitalOcean Spaces.

### File Storage:
- Uses `storages.backends.s3boto3.S3Boto3Storage` to store images in **DigitalOcean Spaces (S3)**.
- **Automatic folder structure:**
  - **Staging**: `staging/media/categories/` and `staging/media/discounts/`
  - **Production**: `production/media/categories/` and `production/media/discounts/`
- Image fields support `null` and `blank`, making them optional.

### Technologies Used:
- **Django ORM**
- **Django GIS (`PointField`)**
- **Django Storages (`django-storages`)**
- **PostGIS for geospatial data**
- **DigitalOcean Spaces (S3-compatible object storage)**
"""

from typing import List, Optional, Dict, Any
from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.core.validators import FileExtensionValidator
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from authentication.models import CustomUser
class Category(models.Model):
    """
    Represents a discount category.

    Attributes:
        name (str): The name of the category.
        image (Optional[FileField]): Image representing the category, stored in S3 (supports SVG).
        created_at (datetime): Timestamp when the category was created.
        updated_at (datetime): Timestamp when the category was last updated.
    """

    name: str = models.CharField(
        max_length=255, unique=True, help_text="Name of the discount category."
    )
    image: Optional[models.FileField] = models.FileField(
        upload_to="categories/",
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg"])],
        null=True,
        blank=True,
        help_text="Image representing the category, stored in S3 (supports SVG).",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Returns the name of the category."""
        return self.name


class Retailer(models.Model):
    """
    Represents a retailer offering discounts.

    Attributes:
        name (str): The name of the retailer.
        contact_info (Optional[str]): Contact details for the retailer.
        location (Point): Geographical location of the retailer.
        owner (User): The user who owns/manages this retailer.
        analytics_data (Dict[str, Any]): Analytics data for the retailer.
        created_at (datetime): Timestamp when the retailer was created.
        updated_at (datetime): Timestamp when the retailer was last updated.
    """

    name: str = models.CharField(
        max_length=255, unique=True, help_text="Name of the retailer."
    )
    contact_info: str = models.TextField(
        blank=True, null=True, help_text="Contact details of the retailer."
    )
    location: models.PointField = models.PointField(
        help_text="Geographic location of the retailer (latitude/longitude)."
    )
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='retailers',
        help_text="User who owns/manages this retailer.",
        null=True,
        blank=True
    )
    analytics_data: Dict[str, Any] = models.JSONField(
        default=dict,
        blank=True,
        help_text="Analytics data for the retailer."
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the retailer was created."
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the retailer was last updated."
    )

    def __str__(self) -> str:
        """Returns a string representation of the retailer."""
        return self.name


class Discount(models.Model):
    """
    Represents a discount or offer provided by a retailer.

    Attributes:
        retailer (Retailer): The retailer offering the discount.
        category (Optional[Category]): The category this discount belongs to.
        description (str): A detailed description of the discount.
        discount_code (str): Unique code for redeeming the discount.
        discount_value (float): The value of the discount (e.g., percentage or fixed amount).
        is_active (bool): Whether the discount is currently active.
        expiration_date (datetime): Expiration date of the discount.
        location (Point): Geographical location where the discount is valid.
        image (Optional[FileField]): An optional image representing the discount (supports SVG).
        created_at (datetime): Timestamp when the discount was created.
        updated_at (datetime): Timestamp when the discount was last updated.
    """

    retailer: models.ForeignKey = models.ForeignKey(
        Retailer, on_delete=models.CASCADE, related_name="discounts"
    )
    category: Optional[models.ForeignKey] = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="discounts"
    )
    description: str = models.TextField()
    discount_code: str = models.CharField(max_length=50, unique=True)
    discount_value: float = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Value of the discount (e.g., amount or percentage).",
        default=0.0
    )
    is_active: bool = models.BooleanField(
        default=True,
        help_text="Whether the discount is currently active.",
    )
    expiration_date: models.DateTimeField = models.DateTimeField(
        help_text="Expiration date of the discount."
    )
    location: models.PointField = models.PointField(
        help_text="Geographic location where the discount is valid (latitude/longitude)."
    )
    image: Optional[models.FileField] = models.FileField(
        upload_to="discounts/",
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg"])],
        null=True,
        blank=True,
        help_text="Optional image representing the discount, stored in S3 (supports SVG).",
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the discount was created."
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the discount was last updated."
    )

    def __str__(self) -> str:
        """Returns a string representation of the discount."""
        return f"{self.retailer.name} - {self.description[:30]}"

    def get_nearby_users(self, radius_km: float = 5.0) -> List[settings.AUTH_USER_MODEL]:
        """Get users within a specified radius of the discount location.
        
        Args:
            radius_km (float): Radius in kilometers to search for users.
            
        Returns:
            List[User]: List of users within the specified radius.
        """
        User = settings.AUTH_USER_MODEL
        
        # Get all users with a location within the radius
        nearby_users = User.objects.filter(
            location__distance_lte=(self.location, D(km=radius_km))
        ).exclude(
            id=self.retailer.owner_id  # Exclude the retailer owner
        )
        
        return list(nearby_users)


class SharedDiscount(models.Model):
    """
    Represents shared discount codes and group purchases.

    Attributes:
        discount (Discount): The discount being shared.
        group_name (str): Name of the group sharing the discount.
        participants (list): List of participant user IDs in the shared discount.
        min_participants (int): Minimum number of participants required.
        max_participants (int): Maximum number of participants allowed.
        status (str): Status of the shared discount (e.g., active, completed, expired).
        created_at (datetime): Timestamp when the shared discount was created.
        updated_at (datetime): Timestamp when the shared discount was last updated.
    """

    discount: Discount = models.ForeignKey(
        Discount,
        on_delete=models.CASCADE,
        related_name="shared_discounts",
        help_text="Discount being shared.",
    )
    group_name: str = models.CharField(
        max_length=255, help_text="Name of the group sharing the discount."
    )
    participants: List[int] = models.JSONField(
        help_text="List of participant user IDs sharing the discount."
    )
    min_participants: int = models.PositiveIntegerField(
        help_text="Minimum number of participants required for the shared discount.",
        default=2
    )
    max_participants: int = models.PositiveIntegerField(
        help_text="Maximum number of participants allowed in the shared discount.",
        default=10
    )
    status: str = models.CharField(
        max_length=50,
        choices=[("active", "Active"), ("completed", "Completed"), ("expired", "Expired")],
        default="active",
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the shared discount was created."
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the shared discount was last updated.",
    )

    def __str__(self) -> str:
        """Returns a formatted string representing the shared discount."""
        return f"{self.group_name} - {self.discount.discount_code}"
