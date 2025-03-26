"""
Views for managing shared discounts in the Discount Discovery System.

This module provides views for listing, creating, updating, and deleting shared discounts.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from geodiscounts.models import SharedDiscount
from geodiscounts.v1.serializers import SharedDiscountSerializer


class SharedDiscountListCreateView(generics.ListCreateAPIView):
    """
    View for listing all shared discounts and creating new ones.

    GET: List all shared discounts
    POST: Create a new shared discount
    """
    queryset = SharedDiscount.objects.all()
    serializer_class = SharedDiscountSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Save the shared discount."""
        serializer.save()


class SharedDiscountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating, and deleting a specific shared discount.

    GET: Retrieve a shared discount
    PUT/PATCH: Update a shared discount
    DELETE: Delete a shared discount
    """
    queryset = SharedDiscount.objects.all()
    serializer_class = SharedDiscountSerializer
    permission_classes = [IsAuthenticated] 