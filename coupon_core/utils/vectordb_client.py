"""
Vector database client for Pinecone.

This module initializes and manages the connection to the Pinecone vector database
and provides helper functions for interacting with the index.


"""

import pinecone
from django.conf import settings


class PineconeClient:
    """
    A client class for managing interactions with the Pinecone vector database.
    """

    def __init__(self) -> None:
        """
        Initialize the Pinecone client with the configuration specified in settings.

        Raises:
            ValueError: If Pinecone initialization fails due to invalid settings.
        """
        try:
            pinecone.init(
                api_key=settings.VECTOR_DB["API_KEY"],
                environment=settings.VECTOR_DB["ENVIRONMENT"],
            )
            self.index_name = settings.VECTOR_DB["NAME"]
        except Exception as e:
            raise ValueError(f"Failed to initialize Pinecone: {str(e)}") from e

    def get_index(self) -> pinecone.Index:
        """
        Retrieve or create the Pinecone index specified in the settings.

        Returns:
            pinecone.Index: The Pinecone index object.

        Raises:
            ValueError: If the index cannot be created or accessed.
        """
        try:
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=settings.VECTOR_DB["DIMENSION"],
                )
            return pinecone.Index(self.index_name)
        except Exception as e:
            raise ValueError(
                f"Failed to retrieve or create Pinecone index: {str(e)}"
            ) from e

    def delete_index(self) -> None:
        """
        Delete the Pinecone index specified in the settings.

        Raises:
            ValueError: If the index cannot be deleted.
        """
        try:
            if self.index_name in pinecone.list_indexes():
                pinecone.delete_index(self.index_name)
        except Exception as e:
            raise ValueError(f"Failed to delete Pinecone index: {str(e)}") from e
