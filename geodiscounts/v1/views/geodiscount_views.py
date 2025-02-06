from typing import List

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

from geodiscounts.models import Discount
from geodiscounts.v1.serializers import DiscountSerializer
from geodiscounts.v1.utils.embedding_utils import generate_embedding
from geodiscounts.v1.utils.ip_geolocation import (
    get_location_from_ip,
    validate_max_distance,
)
from geodiscounts.v1.utils.vector_utils import search_vectors


class DiscountListView(APIView):
    """
    API endpoint to fetch all available discounts.
    """

    def get(self, request) -> Response:
        """
        Returns a list of all discounts in the system.

        Returns:
            Response: JSON response containing the list of discounts.

        Status Codes:
            - 200: Success.
            - 404: No discounts found.
            - 500: Internal server error.
        """
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

    def get(self, request) -> Response:
        """
        Handles GET requests to retrieve nearby discounts.

        Query Parameters:
            - max_distance (optional): Maximum distance (in kilometers) for filtering discounts.

        Returns:
            Response: JSON response containing nearby discounts.

        Status Codes:
            - 200: Success.
            - 400: Validation error.
            - 404: No discounts found.
            - 500: Internal server error.
        """
        try:
            # Ensure the IP address is provided by the middleware
            ip = getattr(request, "client_ip", None)
            if not ip:
                raise ValidationError("Client IP address is not available.")

            # Fetch geolocation from IP
            location = get_location_from_ip(ip)
            if not location:
                raise ValidationError("Unable to determine location from IP address.")

            lat, lon = location["latitude"], location["longitude"]
            user_location = Point(lon, lat, srid=4326)

            # Optional distance filtering
            max_distance = request.GET.get("max_distance")
            if max_distance:
                try:
                    max_distance = validate_max_distance(max_distance)
                except ValueError as e:
                    raise ValidationError(str(e))

            # Query discounts
            discounts = Discount.objects.annotate(
                distance=Distance("location", user_location)
            )
            if max_distance:
                discounts = discounts.filter(
                    distance__lte=max_distance * 1000
                )  # Convert km to meters

            discounts = discounts.order_by("distance")[:10]  # Limit results to top 10
            if not discounts.exists():
                return Response(
                    {"message": "No discounts found near your location."},
                    status=HTTP_404_NOT_FOUND,
                )

            # Serialize and return results
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

    def post(self, request) -> Response:
        """
        Handles POST requests to search for similar discounts.

        Request Body:
            - query (str): A user-provided search query (e.g., a string description or keywords).
            - top_k (int, optional): The number of top results to retrieve (default: 10).

        Returns:
            Response: JSON response containing the top matching discounts.

        Status Codes:
            - 200: Success.
            - 400: Validation error.
            - 500: Internal server error.
        """
        try:
            # Extract and validate the query
            query: str = request.data.get("query")
            if not query or not isinstance(query, str):
                raise ValidationError(
                    "A valid search query must be provided as a string."
                )

            # Generate embedding for the query
            try:
                query_vector: List[float] = generate_embedding(query)
            except Exception as e:
                raise ValidationError(
                    f"Failed to generate embedding for the query: {str(e)}"
                )

            # Validate the top_k parameter
            top_k = request.data.get("top_k", 10)
            try:
                top_k = int(top_k)
                if top_k <= 0:
                    raise ValueError()
            except ValueError:
                raise ValidationError("top_k must be a positive integer.")

            # Search vector database
            search_results = search_vectors(query_vector, top_k=top_k)

            # Extract matching vector IDs
            matching_ids = [result["id"] for result in search_results]

            # Query matching discounts from the database
            discounts = Discount.objects.filter(vector_id__in=matching_ids)
            if not discounts.exists():
                return Response(
                    {"message": "No matching discounts found."},
                    status=HTTP_200_OK,
                )

            # Serialize and return results
            serializer = DiscountSerializer(discounts, many=True)
            return Response(serializer.data, status=HTTP_200_OK)

        except ValidationError as ve:
            return Response({"error": str(ve)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
