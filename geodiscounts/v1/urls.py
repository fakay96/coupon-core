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
    - v1/discounts/refine/   : Refine search based on conversation context.

Author: Your Name
Date: YYYY-MM-DD
"""

from django.urls import path

from geodiscounts.v1.views.discount_category_view import (
    
    CategoryView,
    
)

from geodiscounts.v1.views.geodiscount_views import (
    ConversationalDiscountView,
)

from geodiscounts.v1.views.discount_process_view import (
    ImportDiscountsAPIView

)
app_name = "geodiscounts"

urlpatterns = [
    # Discount URLs

    path('discounts/categories/',CategoryView.as_view(), name='category-view'),
    path('discounts/search/', ConversationalDiscountView.as_view(), name='nearby-discounts'),
    path('discounts/refine/', ConversationalDiscountView.as_view(), name='refine-search'),
    path('discounts/publish/',ImportDiscountsAPIView.as_view(), name='publish-discounts')
]
