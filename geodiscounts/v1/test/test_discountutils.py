import unittest
from typing import Dict
from unittest.mock import MagicMock, patch

from geodiscounts.models import Discount
from geodiscounts.v1.utils.discount_utils import (create_discount,
                                                  delete_discount,
                                                  get_discount_by_vector_id)


class TestDiscountUtils(unittest.TestCase):
    """
    Test cases for discount metadata utilities.

    Includes tests for creating, retrieving, and deleting discount metadata
    stored in the relational database.
    """

    @patch("geodiscounts.models.Discount.objects.create")
    def test_create_discount(self, mock_create: MagicMock) -> None:
        """
        Test creating a new discount in the database successfully.

        Verifies that the `create` method is called with the correct arguments.
        """
        mock_discount = MagicMock()
        mock_create.return_value = mock_discount
        data: Dict[str, str] = {
            "name": "Sample Discount",
            "category": "Food",
            "location": "New York",
            "vector_id": "12345",
            "expiry_date": "2025-01-31T00:00:00Z",
        }
        discount = create_discount(data)
        mock_create.assert_called_once_with(**data)
        self.assertEqual(discount, mock_discount)

    @patch("geodiscounts.models.Discount.objects.get")
    def test_get_discount_by_vector_id_success(self, mock_get: MagicMock) -> None:
        """
        Test retrieving a discount by its vector ID successfully.

        Verifies that the `get` method is called with the correct vector ID.
        """
        mock_discount = MagicMock()
        mock_get.return_value = mock_discount
        vector_id = "12345"
        discount = get_discount_by_vector_id(vector_id)
        mock_get.assert_called_once_with(vector_id=vector_id)
        self.assertEqual(discount, mock_discount)

    @patch("geodiscounts.models.Discount.objects.get")
    def test_get_discount_by_vector_id_not_found(self, mock_get: MagicMock) -> None:
        """
        Test handling when a discount with the given vector ID is not found.

        Verifies that a `DoesNotExist` exception is raised.
        """
        mock_get.side_effect = Discount.DoesNotExist
        vector_id = "nonexistent_id"
        with self.assertRaises(Discount.DoesNotExist):
            get_discount_by_vector_id(vector_id)
        mock_get.assert_called_once_with(vector_id=vector_id)

    @patch("geodiscounts.models.Discount.objects.get")
    def test_delete_discount_success(self, mock_get: MagicMock) -> None:
        """
        Test deleting a discount by its vector ID successfully.

        Verifies that the `delete` method is called on the retrieved discount object.
        """
        mock_discount = MagicMock()
        mock_get.return_value = mock_discount
        vector_id = "12345"
        delete_discount(vector_id)
        mock_get.assert_called_once_with(vector_id=vector_id)
        mock_discount.delete.assert_called_once()

    @patch("geodiscounts.models.Discount.objects.get")
    def test_delete_discount_not_found(self, mock_get: MagicMock) -> None:
        """
        Test handling when attempting to delete a non-existent discount.

        Verifies that a `DoesNotExist` exception is raised.
        """
        mock_get.side_effect = Discount.DoesNotExist
        vector_id = "nonexistent_id"
        with self.assertRaises(Discount.DoesNotExist):
            delete_discount(vector_id)
        mock_get.assert_called_once_with(vector_id=vector_id)
