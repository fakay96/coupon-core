"""
Utility module for handling discount metadata operations.

Provides helper functions for managing relational database entries for discounts.
"""

from typing import Any, Dict

from geodiscounts.models import Discount


def create_discount(data: Dict[str, Any]) -> Discount:
    """
    Create a new discount in the relational database.

    Args:
        data (Dict[str, Any]): Dictionary containing discount details.

    Returns:
        Discount: The created discount object.
    """
    discount = Discount.objects.create(**data)
    return discount


def get_discount_by_vector_id(vector_id: str) -> Discount:
    """
    Retrieve a discount by its associated vector ID.

    Args:
        vector_id (str): The unique ID of the vector.

    Returns:
        Discount: The discount object associated with the vector ID.
    """
    return Discount.objects.get(vector_id=vector_id)


def delete_discount(vector_id: str) -> None:
    """
    Delete a discount by its associated vector ID.

    Args:
        vector_id (str): The unique ID of the vector.
    """
    discount = Discount.objects.get(vector_id=vector_id)
    discount.delete()
