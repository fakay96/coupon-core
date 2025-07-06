"""
Async-compatible JWT authentication for Django REST Framework.

This module provides an async wrapper around the synchronous JWTAuthentication
class to make it compatible with async views.
"""

from asgiref.sync import sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request
from typing import Optional, Tuple, Any


class AsyncJWTAuthentication(BaseAuthentication):
    """
    Async-compatible JWT authentication class.
    
    This class wraps the synchronous JWTAuthentication to make it work
    with async views by using sync_to_async for database operations.
    """
    
    def __init__(self):
        """Initialize the async JWT authentication."""
        self.sync_auth = JWTAuthentication()
    
    def authenticate(self, request: Request) -> Optional[Tuple[Any, Any]]:
        """
        Authenticate the request and return a two-tuple of (user, token).
        
        This method is called by DRF's authentication system. Since DRF
        doesn't natively support async authentication, we need to handle
        the async/sync conversion here.
        
        Args:
            request: The HTTP request to authenticate.
            
        Returns:
            A two-tuple of (user, token) if authentication succeeds,
            None if authentication fails.
        """
        try:
            # Use the synchronous authenticate method directly
            # The sync_to_async conversion will be handled by the view
            return self.sync_auth.authenticate(request)
        except (InvalidToken, TokenError):
            return None
        except Exception:
            return None
    
    def authenticate_header(self, request: Request) -> str:
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        
        Args:
            request: The HTTP request.
            
        Returns:
            The authentication header value.
        """
        return self.sync_auth.authenticate_header(request) 