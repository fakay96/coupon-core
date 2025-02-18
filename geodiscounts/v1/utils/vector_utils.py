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
            self._initialize_database()

    def _initialize_database(self) -> None:
        """
        Initializes the database by enabling the pgvector extension and
        creating the 'vectors' table if it doesn't already exist.
        """
        with self.get_cursor() as cur:
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
