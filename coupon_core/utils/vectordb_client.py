"""
Vector database client for Milvus.

This module initializes and manages the connection to the Milvus vector database
and provides helper functions for interacting with the index.
"""

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from django.conf import settings


class MilvusClient:
    """
    A client class for managing interactions with the Milvus vector database.
    """

    def __init__(self) -> None:
        """
        Initialize the Milvus client with the configuration specified in settings.

        Raises:
            ValueError: If Milvus initialization fails due to invalid settings.
        """
        try:
            connections.connect(
                alias="default",
                host=settings.VECTOR_DB["HOST"],
                port=settings.VECTOR_DB["PORT"],
            )
            self.collection_name = settings.VECTOR_DB["NAME"]
        except Exception as e:
            raise ValueError(f"Failed to initialize Milvus: {str(e)}") from e

    def get_or_create_collection(self) -> Collection:
        """
        Retrieve or create the Milvus collection specified in the settings.

        Returns:
            Collection: The Milvus collection object.

        Raises:
            ValueError: If the collection cannot be created or accessed.
        """
        try:
            if not utility.has_collection(self.collection_name):
                # Define schema for the collection
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.VECTOR_DB["DIMENSION"]),
                ]
                schema = CollectionSchema(fields=fields, description="Vector data collection")
                
                # Create the collection
                collection = Collection(name=self.collection_name, schema=schema)
            else:
                collection = Collection(self.collection_name)

            return collection
        except Exception as e:
            raise ValueError(f"Failed to retrieve or create Milvus collection: {str(e)}") from e

    def delete_collection(self) -> None:
        """
        Delete the Milvus collection specified in the settings.

        Raises:
            ValueError: If the collection cannot be deleted.
        """
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
        except Exception as e:
            raise ValueError(f"Failed to delete Milvus collection: {str(e)}") from e
