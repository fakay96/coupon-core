"""
API URL Configuration for Version 1 (v1)

This file defines the URL patterns for version 1 (v1) of the Discount Discovery System API.
All endpoints are prefixed with `v1/` to ensure modularity and maintainability.

Endpoints:
    - v1/discounts/          : List all available discounts.
    - v1/discounts/nearby/   : Fetch discounts near the user's location (based on IP).
    - v1/retailers/          : List all retailers.
    - v1/retailers/<id>/     : Fetch details of a specific retailer by ID.

Author: Your Name
Date: YYYY-MM-DD
"""

from django.urls import path

from geodiscounts.v1.views.geodiscount_views import (
    DiscountListView,
    NearbyDiscountsView,
)
from geodiscounts.v1.views.retailer_views import RetailerDetailView, RetailerListView

app_name = "geodiscounts_v1"

urlpatterns = [
    # Discount-related endpoints
    path("v1/discounts/", DiscountListView.as_view(), name="discount_list"),
    path(
        "v1/discounts/nearby/",
        NearbyDiscountsView.as_view(),
        name="nearby_discounts",
    ),
    # Retailer-related endpoints
    path("v1/retailers/", RetailerListView.as_view(), name="retailer_list"),
    path(
        "v1/retailers/<int:retailer_id>/",
        RetailerDetailView.as_view(),
        name="retailer_detail",
    ),
]
