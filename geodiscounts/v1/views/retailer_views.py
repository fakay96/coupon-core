from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from rest_framework.views import APIView

from geodiscounts.models import Retailer
from geodiscounts.v1.serializers import RetailerSerializer

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class RetailerListView(APIView):
    """
    API endpoint to fetch all retailers.
    """

    @swagger_auto_schema(
        operation_description="Returns a list of all retailers.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=RetailerSerializer(many=True)
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No retailers available.",
                examples={
                    "application/json": {"message": "No retailers available."}
                }
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message..."
                    }
                }
            ),
        },
    )
    def get(self, request) -> Response:
        """
        Returns a list of all retailers.

        Returns:
            Response: JSON response containing retailer data.

        Status Codes:
            - 200: Success.
            - 404: No retailers found.
            - 500: Internal server error.
        """
        try:
            retailers = Retailer.objects.all()
            if not retailers.exists():
                return Response(
                    {"message": "No retailers available."},
                    status=HTTP_404_NOT_FOUND,
                )
            serializer = RetailerSerializer(retailers, many=True)
            return Response(serializer.data, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RetailerDetailView(APIView):
    """
    API endpoint to fetch a specific retailer by ID.
    """

    @swagger_auto_schema(
        operation_description="Returns details of a specific retailer by their ID.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=RetailerSerializer()
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="Retailer not found.",
                examples={
                    "application/json": {"message": "Retailer not found."}
                }
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message..."
                    }
                }
            ),
        },
    )
    def get(self, request, retailer_id: int) -> Response:
        """
        Returns details of a specific retailer by their ID.

        Args:
            retailer_id (int): ID of the retailer.

        Returns:
            Response: JSON response containing retailer details.

        Status Codes:
            - 200: Success.
            - 404: Retailer not found.
            - 500: Internal server error.
        """
        try:
            retailer = Retailer.objects.filter(id=retailer_id).first()
            if not retailer:
                return Response(
                    {"message": "Retailer not found."},
                    status=HTTP_404_NOT_FOUND,
                )
            serializer = RetailerSerializer(retailer)
            return Response(serializer.data, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
