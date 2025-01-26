import unittest
from unittest.mock import MagicMock, patch

from geodiscounts.v1.utils.vector_utils import (
    delete_vector,
    insert_vector,
    search_vectors,
)


class TestVectorUtils(unittest.TestCase):
    """
    Test cases for vector operations in the Pinecone vector database.

    Includes tests for inserting, searching, and deleting vectors.
    """

    @patch("geodiscounts.v1.utils.vector_utils.pinecone.Index")
    def setUp(self, mock_index: MagicMock) -> None:
        """
        Set up a mock Pinecone index for testing.

        Args:
            mock_index (MagicMock): Mocked Pinecone Index instance.
        """
        self.mock_index = mock_index.return_value

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_insert_vector_success(self, mock_get_index: MagicMock) -> None:
        """
        Test inserting a vector into the Pinecone vector database successfully.

        Verifies that the `upsert` method is called with the correct parameters.
        """
        mock_get_index.return_value = self.mock_index
        vector_id = "test_vector_1"
        values = [0.1, 0.2, 0.3]

        insert_vector(vector_id, values)
        self.mock_index.upsert.assert_called_once_with(
            [{"id": vector_id, "values": values}]
        )

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_insert_vector_failure(self, mock_get_index: MagicMock) -> None:
        """
        Test handling an exception when inserting a vector.

        Verifies that a `ValueError` is raised when `upsert` fails.
        """
        mock_get_index.return_value = self.mock_index
        self.mock_index.upsert.side_effect = Exception("Insert error")

        with self.assertRaises(ValueError) as context:
            insert_vector("test_vector_1", [0.1, 0.2, 0.3])

        self.assertIn("Failed to insert vector", str(context.exception))

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_search_vectors_success(self, mock_get_index: MagicMock) -> None:
        """
        Test searching for similar vectors in the Pinecone vector database successfully.

        Verifies that the `query` method is called with the correct parameters
        and the correct results are returned.
        """
        mock_get_index.return_value = self.mock_index
        query_vector = [0.1, 0.2, 0.3]
        mock_results = {"matches": [{"id": "vector_1", "score": 0.95}]}
        self.mock_index.query.return_value = mock_results

        results = search_vectors(query_vector, top_k=5)
        self.mock_index.query.assert_called_once_with(query_vector, top_k=5)
        self.assertEqual(results, mock_results["matches"])

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_search_vectors_failure(self, mock_get_index: MagicMock) -> None:
        """
        Test handling an exception when searching for vectors.

        Verifies that a `ValueError` is raised when `query` fails.
        """
        mock_get_index.return_value = self.mock_index
        self.mock_index.query.side_effect = Exception("Search error")

        with self.assertRaises(ValueError) as context:
            search_vectors([0.1, 0.2, 0.3], top_k=5)

        self.assertIn("Failed to search vectors", str(context.exception))

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_delete_vector_success(self, mock_get_index: MagicMock) -> None:
        """
        Test deleting a vector from the Pinecone vector database successfully.

        Verifies that the `delete` method is called with the correct parameters.
        """
        mock_get_index.return_value = self.mock_index
        vector_id = "test_vector_1"

        delete_vector(vector_id)
        self.mock_index.delete.assert_called_once_with([vector_id])

    @patch("geodiscounts.v1.utils.vector_utils.pinecone_client.get_index")
    def test_delete_vector_failure(self, mock_get_index: MagicMock) -> None:
        """
        Test handling an exception when deleting a vector.

        Verifies that a `ValueError` is raised when `delete` fails.
        """
        mock_get_index.return_value = self.mock_index
        self.mock_index.delete.side_effect = Exception("Delete error")

        with self.assertRaises(ValueError) as context:
            delete_vector("test_vector_1")

        self.assertIn("Failed to delete vector", str(context.exception))
