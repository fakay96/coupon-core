"""
Tests for utility functions in the Geodiscount API.

This module tests:
1. IP Geolocation utilities
2. Vector utilities
3. Embedding utilities
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock, call, ANY
from django.contrib.gis.geos import Point
from geodiscounts.v1.utils.ip_geolocation import (
    get_location_from_ip,
    cache_location,
    get_cached_location
)
from geodiscounts.v1.utils.vector_utils import (
    calculate_distance,
    calculate_bounding_box,
    is_point_in_radius,
    PostgreSQLVectorClient,
    VECTOR_DIMENSION
)
from geodiscounts.v1.utils.embedding_utils import (
    generate_embedding,
    normalize_embedding
)
import numpy as np
from django.core.cache import cache
import requests
import json
from math import radians, sin, cos, sqrt, atan2
import torch

class IPGeolocationUtilsTest(TestCase):
    """Tests for IP geolocation utilities."""

    def setUp(self):
        """Set up test environment."""
        self.test_ip = '8.8.8.8'
        self.test_location = {
            'latitude': 37.751,
            'longitude': -97.822,
            'city': 'Test City',
            'country': 'Test Country'
        }
        cache.clear()

    @patch('requests.get')
    def test_get_location_from_ip_success(self, mock_get):
        """Test successful IP geolocation lookup."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'latitude': 37.751,
            'longitude': -97.822,
            'city': 'Test City',
            'country_name': 'Test Country'
        }
        mock_get.return_value = mock_response

        location = get_location_from_ip(self.test_ip)
        self.assertEqual(location, self.test_location)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_location_from_ip_failure(self, mock_get):
        """Test failed IP geolocation lookup."""
        mock_get.side_effect = requests.RequestException()
        location = get_location_from_ip(self.test_ip)
        self.assertIsNone(location)

    def test_cache_and_get_location(self):
        """Test caching and retrieving location data."""
        cache_location(self.test_ip, self.test_location)
        cached_location = get_cached_location(self.test_ip)
        self.assertEqual(cached_location, self.test_location)

    def test_get_nonexistent_cached_location(self):
        """Test retrieving non-existent cached location."""
        location = get_cached_location('1.1.1.1')
        self.assertIsNone(location)


class VectorUtilsTest(TestCase):
    """Tests for vector utilities."""

    def setUp(self):
        """Set up test environment."""
        self.lat1, self.lon1 = 41.8902, 12.4924  # Rome
        self.lat2, self.lon2 = 48.8566, 2.3522   # Paris
        self.test_vectors = [
            {'id': '1', 'values': [0.1, 0.2, 0.3], 'metadata': {'name': 'test1'}},
            {'id': '2', 'values': [0.4, 0.5, 0.6], 'metadata': {'name': 'test2'}}
        ]

    def test_calculate_distance(self):
        """Test distance calculation between points."""
        distance = calculate_distance(self.lat1, self.lon1, self.lat2, self.lon2)
        # Approximate distance between Rome and Paris is 1100km
        self.assertAlmostEqual(distance, 1100, delta=100)

    def test_calculate_bounding_box(self):
        """Test bounding box calculation."""
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(
            self.lat1, self.lon1, 100
        )
        self.assertLess(min_lat, self.lat1)
        self.assertGreater(max_lat, self.lat1)
        self.assertLess(min_lon, self.lon1)
        self.assertGreater(max_lon, self.lon1)

    def test_is_point_in_radius(self):
        """Test point in radius check."""
        # Test point within radius
        self.assertTrue(
            is_point_in_radius(self.lat1, self.lon1, self.lat1, self.lon1, 1)
        )
        # Test point outside radius
        self.assertFalse(
            is_point_in_radius(self.lat1, self.lon1, self.lat2, self.lon2, 100)
        )

    @patch('psycopg2.connect')
    @patch('django.conf.settings')
    def test_postgresql_vector_client(self, mock_settings, mock_connect):
        """Test PostgreSQL vector client operations."""
        # Set up mock settings
        mock_settings.DATABASES = {
            'vector_db': {
                'NAME': 'test_db',
                'USER': 'test_user',
                'PASSWORD': 'test_pass',
                'HOST': 'localhost',
                'PORT': 5432,
            }
        }

        # Set up mock connection and cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_conn.closed = False

        # Mock fetchall for search operation
        mock_cur.fetchall.return_value = [(1, 0.5)]

        # Initialize client and perform operations
        client = PostgreSQLVectorClient()
        
        # Test initialization
        client._connect()
        client._initialize_database()

        # Test vector operations
        test_vector = [0.1] * VECTOR_DIMENSION
        client.insert_vector(1, test_vector)
        results = client.search_vectors(test_vector)
        client.delete_vector(1)

        # Verify that all expected SQL statements were executed
        expected_calls = [
            call("CREATE EXTENSION IF NOT EXISTS vector"),
            call(f"""
                CREATE TABLE IF NOT EXISTS vectors (
                    id BIGSERIAL PRIMARY KEY,
                    vector VECTOR({VECTOR_DIMENSION})
                )
            """),
            call("INSERT INTO vectors (id, vector) VALUES (%s, %s)", (1, ANY)),  # Using ANY for vector bytes
            call("""
                    SELECT id, vector <-> %s AS distance
                    FROM vectors
                    ORDER BY vector <-> %s
                    LIMIT %s
                """, (ANY, ANY, 10)),  # Using ANY for vector bytes
            call("DELETE FROM vectors WHERE id = %s", (1,))
        ]

        # Verify each call was made in any order
        for expected_call in expected_calls:
            self.assertTrue(
                any(
                    expected_call.args[0] == actual_call.args[0] and
                    (len(expected_call.args) == 1 or
                     all(e == a or e is ANY
                         for e, a in zip(expected_call.args[1], actual_call.args[1])))
                    for actual_call in mock_cur.execute.call_args_list
                ),
                f"Expected call not found: {expected_call}"
            )

        # Verify search results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 1)
        self.assertEqual(results[0]['score'], 0.5)

        # Clean up
        client.close()
        self.assertTrue(mock_conn.close.called)


class EmbeddingUtilsTest(TestCase):
    """Tests for embedding utilities."""

    def setUp(self):
        """Set up test environment."""
        self.test_text = "Test query for embedding"
        self.test_embedding = [0.1] * 384  # MiniLM-L6-v2 outputs 384-dimensional vectors

    @patch('geodiscounts.v1.utils.embedding_utils.model')
    @patch('geodiscounts.v1.utils.embedding_utils.tokenizer')
    def test_generate_embedding(self, mock_tokenizer, mock_model):
        """Test embedding generation."""
        # Mock tokenizer
        mock_tokenizer.return_value = {
            'input_ids': torch.ones((1, 10)),
            'attention_mask': torch.ones((1, 10))
        }

        # Mock model
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = torch.ones((1, 10, 384))
        mock_model.return_value = mock_outputs

        # Generate embedding
        embedding = generate_embedding(self.test_text)

        # Verify the result
        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 384)  # MiniLM-L6-v2 outputs 384-dimensional vectors
        mock_tokenizer.assert_called_once_with(
            self.test_text,
            return_tensors="pt",
            truncation=True,
            padding=True
        )
        mock_model.assert_called_once_with(
            input_ids=ANY,
            attention_mask=ANY
        )

    def test_normalize_embedding(self):
        """Test embedding normalization."""
        # Test vector
        vector = np.array([1.0, 2.0, 3.0])
        normalized = normalize_embedding(vector)
        
        # Check if the vector is normalized (length should be 1)
        self.assertAlmostEqual(np.linalg.norm(normalized), 1.0)
        
        # Test zero vector
        zero_vector = np.zeros(3)
        normalized_zero = normalize_embedding(zero_vector)
        np.testing.assert_array_equal(normalized_zero, zero_vector)
