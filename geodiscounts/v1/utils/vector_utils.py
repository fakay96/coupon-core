"""
Utility module for managing vector operations in the Milvus vector database.

This module provides functions to insert, search, and delete vectors in the
Milvus vector database. It uses a centralized `MilvusClient` to manage the
connection and interaction with the vector database.

Functions:
    - insert_vector: Inserts a vector into the Milvus collection.
    - search_vectors: Searches for similar vectors in the Milvus collection.
    - delete_vector: Deletes a vector from the Milvus collection.

Dependencies:
    - MilvusClient: A client class that initializes and manages the Milvus connection.
    - Milvus Collection: The collection used for vector storage and retrieval.


"""

from pymilvus import Collection
from coupon_core.utils.vectordb_client import MilvusClient

# Initialize the Milvus client
milvus_client = MilvusClient()

def insert_vector(vector_id: int, values: list[float]) -> None:
    """
    Insert a vector into the Milvus collection.

    Args:
        vector_id (int): The unique identifier for the vector.
        values (list[float]): The vector's embedding values.

    Raises:
        ValueError: If there is an issue with the insertion into Milvus.
    """
    try:
        collection = milvus_client.get_or_create_collection()
        # Insert vector data
        collection.insert([{"id": vector_id, "vector": values}])
        collection.load()
        print(f"Vector with ID {vector_id} inserted successfully.")
    except Exception as e:
        raise ValueError(f"Failed to insert vector with ID '{vector_id}': {str(e)}")


def search_vectors(query_vector: list[float], top_k: int = 10) -> list:
    """
    Search for similar vectors in the Milvus collection.

    Args:
        query_vector (list[float]): The query vector for similarity search.
        top_k (int): The number of top results to return. Defaults to 10.

    Returns:
        list: The search results containing the matches, with IDs and scores.

    Raises:
        ValueError: If there is an issue with the search operation in Milvus.
    """
    try:
        collection = milvus_client.get_or_create_collection()
        # Perform the search
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["id"]
        )
        return [{"id": result.id, "score": result.score} for result in results[0]]
    except Exception as e:
        raise ValueError(f"Failed to search vectors: {str(e)}")


def delete_vector(vector_id: int) -> None:
    """
    Delete a vector from the Milvus collection.

    Args:
        vector_id (int): The unique identifier of the vector to delete.

    Raises:
        ValueError: If there is an issue with the deletion operation in Milvus.
    """
    try:
        collection = milvus_client.get_or_create_collection()
        # Delete vector by ID
        collection.delete(f"id == {vector_id}")
        print(f"Vector with ID {vector_id} deleted successfully.")
    except Exception as e:
        raise ValueError(f"Failed to delete vector with ID '{vector_id}': {str(e)}")
