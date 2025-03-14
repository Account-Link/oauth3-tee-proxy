"""
Middleware package for the OAuth3 TEE Proxy.

This package contains middleware components for request processing
and cross-cutting concerns such as authentication, logging, and error handling.
"""

from .auth import (
    # Main middleware
    AuthMiddleware,
    create_auth_middleware,
    
    # Authentication types and context
    AuthType,
    AuthContext,
    AuthStrategy,
    
    # Strategies
    SessionAuthStrategy,
    OAuth2AuthStrategy,
    
    # Utilities for route handlers
    get_auth_context,
    requires_auth,
    requires_scope
)

__all__ = [
    "AuthMiddleware",
    "create_auth_middleware",
    "AuthType",
    "AuthContext",
    "AuthStrategy",
    "SessionAuthStrategy",
    "OAuth2AuthStrategy",
    "get_auth_context",
    "requires_auth",
    "requires_scope"
]