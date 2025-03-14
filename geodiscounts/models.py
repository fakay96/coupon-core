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

from typing import List, Optional
from django.contrib.gis.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class Category(models.Model):
    """
    Represents a discount category.

    Attributes:
        name (str): The name of the category.
        image (Optional[ImageField]): Image representing the category, stored in S3.
        created_at (datetime): Timestamp when the category was created.
        updated_at (datetime): Timestamp when the category was last updated.
    """

    name: str = models.CharField(
        max_length=255, unique=True, help_text="Name of the discount category."
    )
    image: Optional[models.ImageField] = models.ImageField(
        upload_to="categories/",  # Uses S3 path automatically
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
        null=True,
        blank=True,
        help_text="Image representing the category, stored in S3.",
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
        created_at (datetime): Timestamp when the retailer was created.
        updated_at (datetime): Timestamp when the retailer was last updated.
    """

    name: str = models.CharField(max_length=255, unique=True)
    contact_info: Optional[str] = models.TextField(blank=True, null=True)
    location: models.PointField = models.PointField()
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Returns the name of the retailer."""
        return self.name


class Discount(models.Model):
    """
    Represents a discount or offer provided by a retailer.

    Attributes:
        retailer (Retailer): The retailer offering the discount.
        category (Optional[Category]): The category this discount belongs to.
        description (str): A detailed description of the discount.
        discount_code (str): Unique code for redeeming the discount.
        expiration_date (datetime): Expiration date of the discount.
        location (Point): Geographical location where the discount is valid.
        image (Optional[ImageField]): An optional image representing the discount.
        created_at (datetime): Timestamp when the discount was created.
        updated_at (datetime): Timestamp when the discount was last updated.
    """

    retailer: Retailer = models.ForeignKey(
        Retailer, on_delete=models.CASCADE, related_name="discounts"
    )
    category: Optional[Category] = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="discounts"
    )
    description: str = models.TextField()
    discount_code: str = models.CharField(max_length=50, unique=True)
    expiration_date: models.DateTimeField = models.DateTimeField()
    location: models.PointField = models.PointField()

    image: Optional[models.ImageField] = models.ImageField(
        upload_to="discounts/",  # Uses S3 path automatically
        storage=S3Boto3Storage(),  # Uses S3 from settings
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
        null=True,
        blank=True,
        help_text="Optional image representing the discount, stored in S3.",
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Returns a formatted string representing the discount."""
        return f"{self.retailer.name} - {self.description[:30]}"


class SharedDiscount(models.Model):
    """
    Represents shared discount codes and group purchases.

    Attributes:
        discount (Discount): The discount being shared.
        group_name (str): Name of the group sharing the discount.
        participants (list): List of participants in the shared discount.
        status (str): Status of the shared discount (e.g., active, completed, expired).
        created_at (datetime): Timestamp when the shared discount was created.
        updated_at (datetime): Timestamp when the shared discount was last updated.
    """

    discount: Discount = models.ForeignKey(
        Discount, on_delete=models.CASCADE, related_name="shared_discounts"
    )
    group_name: str = models.CharField(max_length=255)
    participants: List[str] = models.JSONField()
    status: str = models.CharField(
        max_length=50,
        choices=[("active", "Active"), ("completed", "Completed"), ("expired", "Expired")],
        default="active",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Returns a formatted string representing the shared discount."""
        return f"{self.group_name} - {self.discount.discount_code}"
