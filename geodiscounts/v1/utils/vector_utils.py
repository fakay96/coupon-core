"""
Utility module for managing vector operations in the Pinecone vector database.

This module provides functions to insert, search, and delete vectors in the
Pinecone vector database. It uses a centralized `PineconeClient` to manage the
connection and interaction with the vector database.

Functions:
    - insert_vector: Inserts a vector into the Pinecone index.
    - search_vectors: Searches for similar vectors in the Pinecone index.
    - delete_vector: Deletes a vector from the Pinecone index.

Dependencies:
    - PineconeClient: A client class that initializes and manages the Pinecone connection.
    - Pinecone Index: The index used for vector storage and retrieval.

Author: Your Name
Date: YYYY-MM-DD
"""

from coupon_core.utils.vectordb_client import PineconeClient

# Initialize the Pinecone client
pinecone_client = PineconeClient()


def insert_vector(vector_id: str, values: list[float]) -> None:
    """
    Insert a vector into the Pinecone vector database.

    Args:
        vector_id (str): The unique identifier for the vector.
        values (list[float]): The vector's embedding values.

    Raises:
        ValueError: If there is an issue with the insertion into Pinecone.
    """
    try:
        index = pinecone_client.get_index()
        index.upsert([{"id": vector_id, "values": values}])
    except Exception as e:
        raise ValueError(f"Failed to insert vector with ID '{vector_id}': {str(e)}")


def search_vectors(query_vector: list[float], top_k: int = 10) -> dict:
    """
    Search for similar vectors in the Pinecone vector database.

    Args:
        query_vector (list[float]): The query vector for similarity search.
        top_k (int): The number of top results to return. Defaults to 10.

    Returns:
        dict: The search results containing the matches, with IDs and scores.

    Raises:
        ValueError: If there is an issue with the search operation in Pinecone.
    """
    try:
        index = pinecone_client.get_index()
        return index.query(query_vector, top_k=top_k)["matches"]
    except Exception as e:
        raise ValueError(f"Failed to search vectors: {str(e)}")


def delete_vector(vector_id: str) -> None:
    """
    Delete a vector from the Pinecone vector database.

    Args:
        vector_id (str): The unique identifier of the vector to delete.

    Raises:
        ValueError: If there is an issue with the deletion operation in Pinecone.
    """
    try:
        index = pinecone_client.get_index()
        index.delete([vector_id])
    except Exception as e:
        raise ValueError(f"Failed to delete vector with ID '{vector_id}': {str(e)}")
