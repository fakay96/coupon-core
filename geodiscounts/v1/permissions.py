"""Permissions for the geodiscounts app."""

from rest_framework import permissions
from geodiscounts.models import Retailer
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner.
        if hasattr(obj, 'retailer') and hasattr(obj.retailer, 'owner'):
            return obj.retailer.owner == request.user
        return hasattr(obj, 'owner') and obj.owner == request.user

class IsStaffOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow staff users to edit."""

    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to staff users.
        return request.user and request.user.is_staff

class IsMerchantOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a merchant to access it.
    """
    def has_permission(self, request, view):
        # Require authentication for all methods
        if not request.user or not request.user.is_authenticated:
            return False
        
        # For unsafe methods, only allow owners
        if request.method not in permissions.SAFE_METHODS:
            # Check if user owns any retailers
            return Retailer.objects.filter(owner=request.user).exists()
        
        return True

    def has_object_permission(self, request, view, obj):
        # Only allow the owner to access the object
        return obj.owner == request.user

class IsRetailerOwner(permissions.BasePermission):
    """Custom permission to only allow owners of a retailer to edit it."""

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.owner == request.user

    def has_permission(self, request, view):
        # Only allow authenticated users
        return request.user and request.user.is_authenticated

class IsDiscountOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a discount to edit it.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is the owner of the discount.

        Args:
            request: The request being made.
            view: The view handling the request.
            obj: The object being accessed.

        Returns:
            bool: True if the user is the owner or if the request is a safe method.
        """
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the discount.
        return obj.retailer.owner == request.user

    def has_permission(self, request, view):
        # Only allow authenticated users
        return request.user and request.user.is_authenticated

class IsSharedDiscountParticipant(permissions.BasePermission):
    """Custom permission to only allow participants of a shared discount to view it."""

    def has_object_permission(self, request, view, obj):
        # Only participants can view the shared discount
        return request.user.id in obj.participants

    def has_permission(self, request, view):
        # Only allow authenticated users
        return request.user and request.user.is_authenticated 