"""
Models for the Discount Discovery System.

These models define the database structure for retailers, discounts, and shared discounts.
They are designed to support geospatial queries and group discount sharing functionality.
"""

from typing import List

from django.contrib.gis.db import models


class Retailer(models.Model):
    """
    Represents a retailer offering discounts.

    Attributes:
        name (str): The name of the retailer.
        contact_info (str): Contact details for the retailer.
        location (Point): Geographical location of the retailer.
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
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the retailer was created."
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the retailer was last updated.",
    )

    def __str__(self) -> str:
        return self.name


class Discount(models.Model):
    """
    Represents a discount or offer provided by a retailer.

    Attributes:
        retailer (Retailer): The retailer offering the discount.
        description (str): A detailed description of the discount.
        discount_code (str): Unique code for redeeming the discount.
        expiration_date (datetime): Expiration date of the discount.
        location (Point): Geographical location where the discount is valid.
        created_at (datetime): Timestamp when the discount was created.
        updated_at (datetime): Timestamp when the discount was last updated.
    """

    retailer: Retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name="discounts",
        help_text="Retailer providing the discount.",
    )
    description: str = models.TextField(help_text="Description of the discount.")
    discount_code: str = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for redeeming the discount.",
    )
    expiration_date: models.DateTimeField = models.DateTimeField(
        help_text="Expiration date of the discount."
    )
    location: models.PointField = models.PointField(
        help_text="Geographic location where the discount is valid (latitude/longitude)."
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the discount was created."
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the discount was last updated.",
    )

    def __str__(self) -> str:
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
        Discount,
        on_delete=models.CASCADE,
        related_name="shared_discounts",
        help_text="Discount being shared.",
    )
    group_name: str = models.CharField(
        max_length=255, help_text="Name of the group sharing the discount."
    )
    participants: List[str] = models.JSONField(
        help_text="List of participants sharing the discount (e.g., user IDs or emails)."
    )
    status: str = models.CharField(
        max_length=50,
        choices=[
            ("active", "Active"),
            ("completed", "Completed"),
            ("expired", "Expired"),
        ],
        default="active",
        help_text="Status of the shared discount.",
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the shared discount was created.",
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the shared discount was last updated.",
    )

    def __str__(self) -> str:
        return f"{self.group_name} - {self.discount.discount_code}"
