"""
Utility module for managing vector operations in PostgreSQL using the pgvector extension.

This module provides a class-based approach for inserting, searching, and deleting vectors
in a PostgreSQL database. The database configuration is extracted from Django settings (specifically
from the 'vector_db' configuration), and the pgvector extension is used to perform efficient
similarity searches.

The expected vector dimension is defined by VECTOR_DIMENSION.

Usage Example:
    client = PostgreSQLVectorClient()
    client.insert_vector(1, [0.1, 0.2, 0.3, ...])  # Provide VECTOR_DIMENSION number of floats.
    results = client.search_vectors([0.1, 0.2, 0.3, ...])
    client.delete_vector(1)
    client.close()

Dependencies:
    - Django (for settings)
    - psycopg2
    - NumPy
    - pgvector extension on PostgreSQL
"""

import os
import logging
from typing import List, Dict, Optional

from django.conf import settings
import psycopg2
import numpy as np
from psycopg2.extensions import connection as Connection, cursor as Cursor

# Define the expected vector dimension
VECTOR_DIMENSION: int = 1536

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PostgreSQLVectorClient:
    """
    A client for managing vector operations in PostgreSQL using the pgvector extension.
    """

    def __init__(self) -> None:
        self.conn: Optional[Connection] = None
        self._initialized = False

    def _connect(self) -> None:
        """
        Establishes a connection to the PostgreSQL database using the 'vector_db'
        configuration from Django settings if no connection exists or if the current one is closed.
        """
        if self.conn is None or self.conn.closed:
            db_settings = settings.DATABASES.get('vector_db')
            if not db_settings:
                raise ValueError("No 'vector_db' configuration found in Django settings.")
            self.conn = psycopg2.connect(
                dbname=db_settings["NAME"],
                user=db_settings["USER"],
                password=db_settings["PASSWORD"],
                host=db_settings.get("HOST", "localhost"),
                port=db_settings.get("PORT", 5432),
            )
            if not self._initialized:
                self._initialize_database()
                self._initialized = True

    def _initialize_database(self) -> None:
        """
        Initializes the database by enabling the pgvector extension and
        creating the 'vectors' table if it doesn't already exist.
        """
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS vectors (
                    id BIGSERIAL PRIMARY KEY,
                    vector VECTOR({VECTOR_DIMENSION})
                )
            """)
            self.conn.commit()

    def get_cursor(self) -> Cursor:
        """
        Returns a new database cursor. Ensures that a valid connection exists.
        """
        self._connect()
        return self.conn.cursor()

    def close(self) -> None:
        """
        Closes the database connection if it is open.
        """
        if self.conn and not self.conn.closed:
            self.conn.close()

    def insert_vector(self, vector_id: int, values: List[float]) -> None:
        """
        Inserts a vector into the PostgreSQL 'vectors' table.

        Args:
            vector_id (int): The unique identifier for the vector.
            values (List[float]): The vector's embedding values.
        """
        try:
            with self.get_cursor() as cur:
                pg_vector = np.array(values, dtype=np.float32).tobytes()
                cur.execute(
                    "INSERT INTO vectors (id, vector) VALUES (%s, %s)",
                    (vector_id, pg_vector)
                )
                self.conn.commit()
                logger.info(f"Vector with ID {vector_id} inserted successfully.")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert vector {vector_id}: {e}")
            raise ValueError(f"Failed to insert vector {vector_id}: {str(e)}") from e

    def search_vectors(self, query_vector: List[float], top_k: int = 10) -> List[Dict[str, float]]:
        """
        Searches for similar vectors using pgvector's similarity search.

        Args:
            query_vector (List[float]): The query vector for similarity search.
            top_k (int): The number of results to return.

        Returns:
            List[Dict[str, float]]: A list of dictionaries containing vector IDs and similarity scores.
        """
        try:
            with self.get_cursor() as cur:
                pg_query = np.array(query_vector, dtype=np.float32).tobytes()
                cur.execute("""
                    SELECT id, vector <-> %s AS distance
                    FROM vectors
                    ORDER BY vector <-> %s
                    LIMIT %s
                """, (pg_query, pg_query, top_k))
                results = [{"id": row[0], "score": float(row[1])} for row in cur.fetchall()]
                return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ValueError(f"Search failed: {str(e)}") from e

    def delete_vector(self, vector_id: int) -> None:
        """
        Deletes a vector from the PostgreSQL 'vectors' table.

        Args:
            vector_id (int): The ID of the vector to delete.
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM vectors WHERE id = %s", (vector_id,))
                self.conn.commit()
                logger.info(f"Vector with ID {vector_id} deleted successfully.")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to delete vector {vector_id}: {e}")
            raise ValueError(f"Failed to delete vector {vector_id}: {str(e)}") from e

"""Utility functions for vector calculations and distance measurements."""

from math import radians, sin, cos, sqrt, atan2

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    
    Args:
        lat1 (float): Latitude of first point
        lon1 (float): Longitude of first point
        lat2 (float): Latitude of second point
        lon2 (float): Longitude of second point
        
    Returns:
        float: Distance between points in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of earth in kilometers
    r = 6371
    
    # Calculate distance
    distance = r * c
    
    return distance

def calculate_bounding_box(lat, lon, radius_km):
    """
    Calculate a bounding box given a center point and radius.
    
    Args:
        lat (float): Center latitude
        lon (float): Center longitude
        radius_km (float): Radius in kilometers
        
    Returns:
        tuple: (min_lat, max_lat, min_lon, max_lon)
    """
    # Rough approximation: 1 degree = 111km
    lat_change = radius_km / 111.0
    lon_change = radius_km / (111.0 * cos(radians(lat)))
    
    return (
        lat - lat_change,  # min lat
        lat + lat_change,  # max lat
        lon - lon_change,  # min lon
        lon + lon_change   # max lon
    )

def is_point_in_radius(center_lat, center_lon, point_lat, point_lon, radius_km):
    """
    Check if a point is within a given radius of a center point.
    
    Args:
        center_lat (float): Center point latitude
        center_lon (float): Center point longitude
        point_lat (float): Point to check latitude
        point_lon (float): Point to check longitude
        radius_km (float): Radius in kilometers
        
    Returns:
        bool: True if point is within radius, False otherwise
    """
    distance = calculate_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km
