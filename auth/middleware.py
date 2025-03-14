"""
Authentication Middleware
========================

This module provides middleware for handling JWT-based authentication
throughout the application. It extracts and validates JWT tokens from
either session cookies or Authorization headers and makes the authenticated
user available to route handlers.
"""

import logging
from typing import Optional, Callable, Dict, Any, List
from functools import wraps

from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth.jwt_service import validate_token, refresh_token_if_needed

# Set up logger
logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling JWT authentication.
    
    This middleware extracts JWT tokens from the request, validates them,
    and attaches the authenticated user to the request state for use by
    route handlers.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        public_paths: List[str] = None,
        protected_paths: List[str] = None
    ):
        """
        Initialize the authentication middleware.
        
        Args:
            app: The ASGI application
            public_paths: List of paths that require no authentication (supports wildcards)
            protected_paths: List of paths that specifically require authentication (supports wildcards)
        """
        super().__init__(app)
        self.public_paths = public_paths or [
            "/",
            "/static/*",
            "/auth/register",
            "/auth/login",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.protected_paths = protected_paths or [
            "/profile",
            "/profile/*",
            "/dashboard",
            "/api/*"
        ]
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request through the middleware.
        
        This method:
        1. Checks if the path requires authentication
        2. Extracts the JWT token from cookie or Authorization header
        3. Validates the token and gets the user
        4. Attaches user and token data to request state
        5. Refreshes token if needed and updates cookie
        
        Args:
            request: The incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            The HTTP response
        """
        path = request.url.path
        
        # Initialize authentication state
        request.state.user = None
        request.state.token = None
        request.state.is_authenticated = False
        
        # Check if path is public
        if self._is_public_path(path):
            return await call_next(request)
        
        # Try to get token from cookie first, then Authorization header
        token = request.cookies.get("access_token")
        if not token and "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
        
        # If token exists, validate it
        if token:
            db = next(get_db())
            token_data = validate_token(token, db, request)
            
            if token_data:
                # Attach user and token data to request
                request.state.user = token_data["user"]
                request.state.token = token_data
                request.state.is_authenticated = True
        
        # Check if authentication is required but not provided
        if self._requires_auth(path) and not request.state.is_authenticated:
            # Return appropriate response based on path
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"}
                )
            else:
                return RedirectResponse(url="/auth/login")
        
        # Proceed with request
        response = await call_next(request)
        
        # Refresh token if needed
        if (
            request.state.is_authenticated and
            request.state.token["policy"] == "passkey" and
            token in request.cookies.values()
        ):
            token_data = refresh_token_if_needed(
                token_data=request.state.token,
                request=request,
                response=response
            )
            
            if token_data:
                logger.debug(f"Refreshed token for user {request.state.user.id}")
        
        return response
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (requires no authentication).
        
        Args:
            path: Request path
            
        Returns:
            True if path is public, False otherwise
        """
        # Check exact matches
        if path in self.public_paths:
            return True
        
        # Check wildcards
        for public_path in self.public_paths:
            if public_path.endswith("*") and path.startswith(public_path[:-1]):
                return True
        
        return False
    
    def _requires_auth(self, path: str) -> bool:
        """
        Check if a path requires authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if authentication is required, False otherwise
        """
        # Check exact matches
        if path in self.protected_paths:
            return True
        
        # Check wildcards
        for protected_path in self.protected_paths:
            if protected_path.endswith("*") and path.startswith(protected_path[:-1]):
                return True
        
        return False

# Dependency for getting the current user
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency for getting the current authenticated user.
    
    Args:
        request: The request object
        db: Database session
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    return user

# Decorator for requiring authentication in route handlers
def require_auth(func: Callable) -> Callable:
    """
    Decorator for requiring authentication in route handlers.
    
    Args:
        func: The route handler function
        
    Returns:
        Decorated function that checks for authentication
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get request from args or kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request and "request" in kwargs:
            request = kwargs["request"]
        
        if not request:
            raise ValueError("Request object not found in function arguments")
        
        # Check authentication
        if not getattr(request.state, "is_authenticated", False):
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper