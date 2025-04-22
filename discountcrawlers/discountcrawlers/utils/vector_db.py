"""Vector database utilities for discount search.

This module provides functions for managing vector embeddings and search
for the Discount model using Redis as a vector database.
"""

from __future__ import annotations
import logging
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from django.contrib.gis.geos import Point
from django.conf import settings

from .redis_utils import get_redis_client
from .embedding import generate_embedding

LOGGER: logging.Logger = logging.getLogger(__name__)

# Redis index configuration
DISCOUNT_INDEX = "discounts"
VECTOR_DIM = 1024  # Dimension of Gemini embeddings

def initialize_vector_index() -> bool:
    """Initialize the Redis vector search index for discounts.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Check if index exists
        try:
            client.ft().info(DISCOUNT_INDEX)
            return True
        except:
            # Create new index if it doesn't exist
            schema = (
                f"ON JSON PREFIX 1 discount: SCHEMA "
                f"$.retailer AS retailer TEXT "
                f"$.category AS category TEXT "
                f"$.description AS description TEXT "
                f"$.discount_code AS discount_code TEXT "
                f"$.discount_value AS discount_value NUMERIC "
                f"$.is_active AS is_active TAG "
                f"$.expiration_date AS expiration_date NUMERIC "
                f"$.location AS location GEO "
                f"$.image_url AS image_url TEXT "
                f"$.created_at AS created_at NUMERIC "
                f"$.updated_at AS updated_at NUMERIC "
                f"$.embedding AS embedding VECTOR FLAT 6 TYPE FLOAT32 DIM {VECTOR_DIM} DISTANCE_METRIC COSINE"
            )
            
            client.ft().create_index(schema)
            LOGGER.info(f"Created vector index: {DISCOUNT_INDEX}")
            return True
            
    except Exception as e:
        LOGGER.error(f"Failed to initialize vector index: {str(e)}")
        return False

def store_discount_vector(discount: Any) -> bool:
    """Store a discount's vector embedding in Redis.
    
    Args:
        discount: Discount model instance
        
    Returns:
        True if storage was successful, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Generate embedding from description
        embedding = generate_embedding(discount.description)
        if embedding is None:
            return False
            
        # Prepare discount data
        discount_data = {
            "retailer": discount.retailer.name,
            "category": discount.category.name if discount.category else None,
            "description": discount.description,
            "discount_code": discount.discount_code,
            "discount_value": float(discount.discount_value),
            "is_active": str(discount.is_active).lower(),
            "expiration_date": discount.expiration_date.timestamp(),
            "location": {
                "type": "Point",
                "coordinates": [discount.location.x, discount.location.y]
            },
            "image_url": discount.image.url if discount.image else None,
            "created_at": discount.created_at.timestamp(),
            "updated_at": discount.updated_at.timestamp(),
            "embedding": embedding.tolist()
        }
        
        # Store in Redis
        key = f"discount:{discount.id}"
        client.json().set(key, ".", discount_data)
        
        LOGGER.info(f"Stored vector for discount: {discount.id}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Failed to store discount vector: {str(e)}")
        return False

def search_discounts(
    query: str,
    location: Optional[Point] = None,
    radius_km: float = 5.0,
    categories: Optional[List[str]] = None,
    min_discount: Optional[float] = None,
    max_discount: Optional[float] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search for discounts using vector similarity and filters.
    
    Args:
        query: Search query text
        location: Optional location to filter by
        radius_km: Radius in kilometers for location filter
        categories: Optional list of categories to filter by
        min_discount: Minimum discount value
        max_discount: Maximum discount value
        limit: Maximum number of results to return
        
    Returns:
        List of matching discount items with similarity scores
    """
    try:
        client = get_redis_client()
        if not client:
            return []
            
        # Generate query embedding
        query_embedding = generate_embedding(query)
        if query_embedding is None:
            return []
            
        # Build query
        search_query = {
            "vector": query_embedding.tolist(),
            "top_k": limit,
            "with_payload": True,
            "with_vectors": False
        }
        
        # Add filters
        filters = []
        
        # Location filter
        if location:
            filters.append({
                "location": {
                    "$within": {
                        "radius": radius_km,
                        "center": [location.x, location.y]
                    }
                }
            })
            
        # Category filter
        if categories:
            filters.append({
                "category": {"$in": categories}
            })
            
        # Discount value filter
        if min_discount is not None or max_discount is not None:
            price_filter = {}
            if min_discount is not None:
                price_filter["$gte"] = min_discount
            if max_discount is not None:
                price_filter["$lte"] = max_discount
            filters.append({
                "discount_value": price_filter
            })
            
        # Active discount filter
        filters.append({
            "is_active": "true"
        })
        
        # Expiration date filter
        filters.append({
            "expiration_date": {"$gt": datetime.now().timestamp()}
        })
        
        if filters:
            search_query["filter"] = {"$and": filters}
            
        # Execute search
        results = client.ft().search(
            query=search_query,
            index_name=DISCOUNT_INDEX
        )
        
        # Process results
        discounts = []
        for result in results.docs:
            try:
                item = json.loads(result.payload)
                # Add similarity score
                item["similarity_score"] = result.score
                discounts.append(item)
            except json.JSONDecodeError as e:
                LOGGER.error(f"Failed to parse Redis result: {str(e)}")
                continue
                
        return discounts
        
    except Exception as e:
        LOGGER.error(f"Error searching discounts: {str(e)}")
        return [] 