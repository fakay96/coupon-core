"""
API URL Configuration for Version 1 (v1)

This file defines the URL patterns for version 1 (v1) of the Discount Discovery System API.
All endpoints are prefixed with `v1/` to ensure modularity and maintainability.

Endpoints:
    - v1/discounts/          : List all available discounts.
    - v1/discounts/nearby/   : Fetch discounts near the user's location (based on IP).
    - v1/retailers/          : List all retailers.
    - v1/retailers/<id>/     : Fetch details of a specific retailer by ID.
    - v1/shared-discounts/   : List all shared discounts.
    - v1/shared-discounts/<id>/ : Fetch details of a specific shared discount by ID.

Author: Your Name
Date: YYYY-MM-DD
"""

from django.urls import path

from geodiscounts.v1.views.discount_views import (
    DiscountListCreateView,
    DiscountDetailView,
    NearbyDiscountsView,
    SearchDiscountsView,
    CategoryView,
)
from geodiscounts.v1.views.retailer_views import (
    RetailerListCreateView,
    RetailerDetailView,
    NearbyRetailersView,
    RetailerAnalyticsView,
)
from geodiscounts.v1.views.shared_discount_views import (
    SharedDiscountListCreateView,
    SharedDiscountDetailView,
)

app_name = "geodiscounts"

urlpatterns = [
    # # Discount URLs
    path('discounts/', DiscountListCreateView.as_view(), name='discount-list'),
    path('discounts/<int:pk>/', DiscountDetailView.as_view(), name='discount-detail'),
    path('discounts/nearby/', NearbyDiscountsView.as_view(), name='discount-nearby'),
    path('discounts/search/', SearchDiscountsView.as_view(), name='discount-search'),
    path('discounts/categories/', CategoryView.as_view(), name='discount-categories'),
    
    # Retailer URLs
    path('retailers/', RetailerListCreateView.as_view(), name='retailer-list'),
    path('retailers/<int:pk>/', RetailerDetailView.as_view(), name='retailer-detail'),
    path('retailers/nearby/', NearbyRetailersView.as_view(), name='retailer-nearby'),
    path('retailers/<int:pk>/analytics/', RetailerAnalyticsView.as_view(), name='merchant-analytics'),
    
    # Shared Discount URLs
    path('shared-discounts/', SharedDiscountListCreateView.as_view(), name='shared-discount-list'),
    path('shared-discounts/<int:pk>/', SharedDiscountDetailView.as_view(), name='shared-discount-detail'),
]
