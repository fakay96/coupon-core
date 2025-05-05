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
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from authentication.models import CustomUser
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from coupon_core.utils.logging import geo_logger, geo_structured_logger

User = settings.AUTH_USER_MODEL

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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the category with logging."""
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Category saved successfully",
                "category_save",
                {
                    'category_id': self.id,
                    'name': self.name
                }
            )
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error saving category",
                "category_save",
                e,
                {
                    'name': self.name
                }
            )
            raise


class Retailer(models.Model):
    """
    Represents a retailer offering discounts.

    Attributes:
        name (str): The name of the retailer.
        contact_info (Optional[str]): Contact details for the retailer.
        location (Point): Geographical location of the retailer.
        owner_id (int): ID of the user who owns/manages this retailer (cross-shard reference).
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
    owner_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID of the user who owns/manages this retailer (cross-shard reference)."
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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the retailer with logging."""
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Retailer saved successfully",
                "retailer_save",
                {
                    'retailer_id': self.id,
                    'name': self.name,
                    'owner_id': self.owner_id
                }
            )
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error saving retailer",
                "retailer_save",
                e,
                {
                    'name': self.name,
                    'owner_id': self.owner_id
                }
            )
            raise

class Discount(models.Model):
    """
    Represents a discount or offer provided by a retailer.

    Using cross-shard references with the help of the GeoDiscountsRouter.

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

    retailer = models.ForeignKey(
        'Retailer', on_delete=models.CASCADE, related_name="discounts"
    )
    category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True, related_name="discounts"
    )
    description = models.TextField()
    discount_code = models.CharField(max_length=50, unique=True)
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Value of the discount (e.g., amount or percentage).",
        default=0.0
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the discount is currently active.",
    )
    expiration_date = models.DateTimeField(
        help_text="Expiration date of the discount."
    )
    location = models.PointField(
        help_text="Geographic location where the discount is valid (latitude/longitude)."
    )
    image = models.FileField(
        upload_to="discounts/",
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg"])],
        null=True,
        blank=True,
        help_text="Optional image representing the discount, stored in S3 (supports SVG).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the discount was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the discount was last updated."
    )

    def __str__(self) -> str:
        """Returns a string representation of the discount."""
        return f"{self.retailer.name} - {self.description[:30]}"

    def get_nearby_users(self, radius_km: float = 5.0) -> List[CustomUser]:
        """Get users within a specified radius of the discount location.
        
        Uses the database router to query the User model in the authentication shard.
        
        Args:
            radius_km (float): Radius in kilometers to search for users.
            
        Returns:
            List[CustomUser]: List of users within the specified radius.
        """
        # The router automatically directs this query to the authentication_shard
        nearby_users = CustomUser.objects.using('authentication_shard').filter(
            location__distance_lte=(self.location, D(km=radius_km))
        ).exclude(
            id=self.retailer.owner_id  # Exclude the retailer owner
        )
        
        return list(nearby_users)

    def clean(self) -> None:
        """Validate the discount data."""
        if self.expiration_date <= timezone.now():
            geo_structured_logger.warning(
                geo_logger,
                "Discount expiration date is in the past",
                "discount_clean",
                {
                    'discount_id': self.id,
                    'expiration_date': self.expiration_date.isoformat()
                }
            )
            raise ValidationError(_("Expiration date must be in the future"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the discount with logging."""
        try:
            self.full_clean()
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Discount saved successfully",
                "discount_save",
                {
                    'discount_id': self.id,
                    'retailer_id': self.retailer.id,
                    'category_id': self.category.id if self.category else None,
                    'is_active': self.is_active
                }
            )
        except ValidationError as ve:
            geo_structured_logger.error(
                geo_logger,
                "Validation error saving discount",
                "discount_save",
                ve,
                {
                    'retailer_id': self.retailer.id,
                    'category_id': self.category.id if self.category else None
                }
            )
            raise
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error saving discount",
                "discount_save",
                e,
                {
                    'retailer_id': self.retailer.id,
                    'category_id': self.category.id if self.category else None
                }
            )
            raise



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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the shared discount with logging."""
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Shared discount saved successfully",
                "shared_discount_save",
                {
                    'shared_discount_id': self.id,
                    'discount_id': self.discount.id,
                    'group_name': self.group_name,
                    'status': self.status
                }
            )
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error saving shared discount",
                "shared_discount_save",
                e,
                {
                    'discount_id': self.discount.id,
                    'group_name': self.group_name
                }
            )
            raise

class WebSocketDiscountRequest(models.Model):
    """
    Tracks WebSocket discount requests and their status.

    In a sharded architecture where users are in a different database shard,
    we store the user_id as a regular field instead of a direct foreign key.

    Attributes:
        request_id (str): Unique identifier for the request
        user_id (int): ID of the user who made the request (stored as value, not FK)
        location (Point): The location for the discount search
        radius (float): Search radius in kilometers
        category (Optional[Category]): The category to filter by
        status (str): Current status of the request
        results (Dict[str, Any]): The results of the request
        conversation_history (List[Dict[str, Any]]): History of conversation messages
        websocket_url (str): URL for WebSocket connection
        created_at (datetime): When the request was created
        updated_at (datetime): When the request was last updated
    """
    
    request_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the WebSocket request"
    )
    # Store user ID as integer instead of foreign key
    user_id = models.BigIntegerField(
        help_text="ID of the user who made the request"
    )
    location = models.PointField(
        help_text="Location for the discount search"
    )
    radius = models.FloatField(
        default=10.0,
        help_text="Search radius in kilometers"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="websocket_requests",
        help_text="Category to filter by"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed")
        ],
        default="pending",
        help_text="Current status of the request"
    )
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Results of the request"
    )
    conversation_history = models.JSONField(
        default=list,
        blank=True,
        help_text="History of conversation messages"
    )
    websocket_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL for WebSocket connection"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the request was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the request was last updated"
    )
    # Optional: Store additional user information for quick access
    user_email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text="User email for quick reference without cross-shard query"
    )

    def __str__(self) -> str:
        """Returns a formatted string representing the request."""
        return f"Request {self.request_id} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the WebSocket request with logging."""
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "WebSocket request saved successfully",
                "websocket_request_save",
                {
                    'request_id': str(self.request_id),
                    'user_id': self.user_id,
                    'status': self.status
                }
            )
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error saving WebSocket request",
                "websocket_request_save",
                e,
                {
                    'request_id': str(self.request_id),
                    'user_id': self.user_id
                }
            )
            raise

    class Meta:
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['user_id']),  
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

class Location(models.Model):
    """
    Represents a geographical location with a radius.

    Attributes:
        name (str): Name of the location.
        latitude (float): Latitude coordinate.
        longitude (float): Longitude coordinate.
        radius (float): Radius in meters for the location.
        is_valid (bool): Whether the location is valid.
        last_updated (datetime): When the location was last updated.
    """

    name: str = models.CharField(
        max_length=255,
        help_text="Name of the location."
    )
    latitude: float = models.FloatField(
        validators=[
            MinValueValidator(-90.0),
            MaxValueValidator(90.0)
        ],
        help_text="Latitude coordinate (-90 to 90)."
    )
    longitude: float = models.FloatField(
        validators=[
            MinValueValidator(-180.0),
            MaxValueValidator(180.0)
        ],
        help_text="Longitude coordinate (-180 to 180)."
    )
    radius: float = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Radius in meters for the location."
    )
    is_valid: bool = models.BooleanField(
        default=True,
        help_text="Whether the location is valid."
    )
    last_updated: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="When the location was last updated."
    )

    def __str__(self) -> str:
        """Returns a string representation of the location."""
        return f"{self.name} ({self.latitude}, {self.longitude})"

    def calculate_distance(self, other: 'Location') -> float:
        """Calculate distance to another location in meters.
        
        Args:
            other (Location): The other location to calculate distance to.
            
        Returns:
            float: Distance in meters.
        """
        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        
        point1 = Point(self.longitude, self.latitude)
        point2 = Point(other.longitude, other.latitude)
        
        return point1.distance(point2) * 100000  # Convert to meters

    def overlaps_with(self, other: 'Location') -> bool:
        """Check if this location overlaps with another location.
        
        Args:
            other (Location): The other location to check.
            
        Returns:
            bool: True if locations overlap, False otherwise.
        """
        distance = self.calculate_distance(other)
        return distance < (self.radius + other.radius)

    def get_bounding_box(self) -> tuple:
        """Get the bounding box for this location.
        
        Returns:
            tuple: (min_lat, min_lng, max_lat, max_lng)
        """
        # Convert radius from meters to degrees (approximate)
        lat_radius = self.radius / 111000  # 111km per degree
        lng_radius = self.radius / (111000 * abs(self.latitude))
        
        return (
            self.latitude - lat_radius,
            self.longitude - lng_radius,
            self.latitude + lat_radius,
            self.longitude + lng_radius
        )

    def to_geojson(self) -> Dict[str, Any]:
        """Convert location to GeoJSON format.
        
        Returns:
            Dict[str, Any]: GeoJSON representation of the location.
        """
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [self.longitude, self.latitude]
            },
            'properties': {
                'name': self.name,
                'radius': self.radius
            }
        }

    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_valid']),
            models.Index(fields=['last_updated']),
        ]
        ordering = ['-last_updated']
