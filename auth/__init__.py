"""
Authentication module for the OAuth3 TEE Proxy.

This module provides comprehensive authentication services including:
- JWT token management
- WebAuthn/Passkey authentication
- User session handling
- Authentication middleware
"""

from .jwt_service import (
    create_token,
    validate_token,
    refresh_token_if_needed,
    revoke_token,
    revoke_all_user_tokens
)

from .passkey_service import (
    PasskeyService,
    get_passkey_service
)

from .middleware import (
    AuthMiddleware,
    get_current_user
)

__all__ = [
    # JWT Token management
    "create_token",
    "validate_token",
    "refresh_token_if_needed",
    "revoke_token",
    "revoke_all_user_tokens",
    
    # Passkey service
    "PasskeyService",
    "get_passkey_service",
    
    # Middleware
    "AuthMiddleware",
    "get_current_user"
]