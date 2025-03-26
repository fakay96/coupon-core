"""
API Views for the Discount Discovery System.

This module contains API endpoints for:
- Fetching all available discount categories (cached for 30 minutes).
- Fetching all available discounts.
- Finding nearby discounts based on user IP.
- Searching for discounts using vector embeddings.

Each endpoint is documented and uses Django Rest Framework (DRF) for serialization.
Caching is enabled where applicable to optimize performance.

Author: Your Name
Date: YYYY-MM-DD
"""

from typing import List

from django.core.cache import cache
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from rest_framework.views import APIView

from geodiscounts.models import Discount, Category
from geodiscounts.v1.serializers import DiscountSerializer, CategorySerializer
from geodiscounts.v1.utils.embedding_utils import generate_embedding
from geodiscounts.v1.utils.ip_geolocation import (
    get_location_from_ip,
    validate_max_distance,
)
from geodiscounts.v1.utils.vector_utils import PostgreSQLVectorClient

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

client = PostgreSQLVectorClient()


class CategoryView(APIView):
    """
    API endpoint to retrieve all available discount categories.

    - Categories are cached for 30 minutes to optimize performance and reduce database load.
    - Uses atomic caching to reduce redundant queries.
    """
    # Removed serializer_class to prevent automatic inclusion in the Swagger spec.
    permission_classes = [AllowAny]  # Public access

    @swagger_auto_schema(
        operation_description="Fetches all discount categories. Caches results for 30 minutes.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "image": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        },
                    ),
                ),
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No categories found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(type=openapi.TYPE_STRING),
                        "details": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def get(self, request) -> Response:
        cache_key = "categories_list"
        try:
            categories = cache.get(cache_key)
            if categories is None:
                category_queryset = Category.objects.only("id", "name", "image")
                if not category_queryset.exists():
                    return Response(
                        {"message": "No categories available."},
                        status=HTTP_404_NOT_FOUND,
                    )
                serializer = CategorySerializer(category_queryset, many=True)
                categories = serializer.data
                cache.set(cache_key, categories, timeout=1800)  # Cache for 30 minutes
            return Response(categories, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DiscountListView(APIView):
    """
    API endpoint to fetch all available discounts.
    """
    @swagger_auto_schema(
        operation_description="Returns a list of all discounts in the system.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "retailer": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    # Add additional retailer fields if needed.
                                },
                            ),
                            "description": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_value": openapi.Schema(type=openapi.TYPE_NUMBER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "expiration_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "location": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        },
                    ),
                ),
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No discounts found.",
                examples={"application/json": {"message": "No discounts available."}},
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message...",
                    }
                },
            ),
        },
    )
    def get(self, request) -> Response:
        try:
            discounts = Discount.objects.all()
            if not discounts.exists():
                return Response(
                    {"message": "No discounts available."},
                    status=HTTP_404_NOT_FOUND,
                )
            serializer = DiscountSerializer(discounts, many=True)
            return Response(serializer.data, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NearbyDiscountsView(APIView):
    """
    API endpoint to fetch discounts near a user's location based on their IP address.

    Allows optional filtering by a maximum distance (in kilometers).
    """
    max_distance_param = openapi.Parameter(
        "max_distance",
        openapi.IN_QUERY,
        description="Maximum distance (in kilometers) for filtering discounts.",
        type=openapi.TYPE_NUMBER,
        required=False,
    )

    @swagger_auto_schema(
        operation_description="Retrieve discounts near the user's location (based on IP address) with an optional max_distance filter.",
        manual_parameters=[max_distance_param],
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "retailer": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "description": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_value": openapi.Schema(type=openapi.TYPE_NUMBER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "expiration_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "location": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "distance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Distance in meters"),
                        },
                    ),
                ),
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Validation error.",
                examples={"application/json": {"error": "Detailed validation error message."}},
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No discounts found.",
                examples={"application/json": {"message": "No discounts found near your location."}},
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message...",
                    }
                },
            ),
        },
    )
    def get(self, request) -> Response:
        try:
            ip = getattr(request, "client_ip", None)
            if not ip:
                raise ValidationError("Client IP address is not available.")

            location = get_location_from_ip(ip)
            if not location:
                raise ValidationError("Unable to determine location from IP address.")

            lat, lon = location["latitude"], location["longitude"]
            user_location = Point(lon, lat, srid=4326)

            max_distance = request.GET.get("max_distance")
            if max_distance:
                try:
                    max_distance = validate_max_distance(max_distance)
                except ValueError as e:
                    raise ValidationError(str(e))

            discounts = Discount.objects.annotate(
                distance=Distance("location", user_location)
            )
            if max_distance:
                discounts = discounts.filter(distance__lte=max_distance * 1000)
            discounts = discounts.order_by("distance")[:10]
            if not discounts.exists():
                return Response(
                    {"message": "No discounts found near your location."},
                    status=HTTP_404_NOT_FOUND,
                )

            serializer = DiscountSerializer(discounts, many=True)
            return Response(serializer.data, status=HTTP_200_OK)
        except ValidationError as ve:
            return Response({"error": str(ve)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SearchDiscountsView(APIView):
    """
    API endpoint to search for discounts using a query string.

    The query is embedded into a vector, which is then used to search the vector database.
    """
    search_request_body = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "query": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="A user-provided search query (e.g., a description or keywords).",
                example="50% off shoes",
            ),
            "top_k": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="The number of top results to retrieve (default: 10).",
                example=10,
            ),
        },
        required=["query"],
    )

    @swagger_auto_schema(
        operation_description="Search for discounts based on a query string by embedding the query and searching the vector database.",
        request_body=search_request_body,
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "retailer": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "description": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_value": openapi.Schema(type=openapi.TYPE_NUMBER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "expiration_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "location": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        },
                    ),
                ),
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Validation error.",
                examples={"application/json": {"error": "A valid search query must be provided as a string."}},
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={"application/json": {"error": "An unexpected error occurred.", "details": "Detailed error message..."}},
            ),
        },
    )
    def post(self, request) -> Response:
        try:
            query: str = request.data.get("query")
            if not query or not isinstance(query, str):
                raise ValidationError("A valid search query must be provided as a string.")

            try:
                query_vector: List[float] = generate_embedding(query)
            except Exception as e:
                raise ValidationError(f"Failed to generate embedding for the query: {str(e)}")

            top_k = request.data.get("top_k", 10)
            try:
                top_k = int(top_k)
                if top_k <= 0:
                    raise ValueError()
            except ValueError:
                raise ValidationError("top_k must be a positive integer.")

            search_results = client.search_vectors(query_vector, top_k=top_k)
            matching_ids = [result["id"] for result in search_results]
            discounts = Discount.objects.filter(vector_id__in=matching_ids)
            if not discounts.exists():
                return Response({"message": "No matching discounts found."}, status=HTTP_200_OK)

            serializer = DiscountSerializer(discounts, many=True)
            return Response(serializer.data, status=HTTP_200_OK)
        except ValidationError as ve:
            return Response({"error": str(ve)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
