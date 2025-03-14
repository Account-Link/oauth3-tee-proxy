"""
Authentication Middleware
========================

This module provides a comprehensive authentication middleware for the OAuth3 TEE Proxy.
It supports multiple authentication strategies and provides a unified interface
for authenticating users and authorizing requests.

The middleware evaluates authentication according to multiple configured strategies,
loads user information, and attaches it to the request state for use by route handlers.

Key features:
- Support for multiple authentication strategies (session, OAuth2, etc.)
- Extensible design for adding new authentication methods
- Unified user context across all routes
- Support for different authentication requirements per route
"""

import inspect
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Dict, List, Optional, Type, Any, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from database import get_db
from models import User

logger = logging.getLogger(__name__)

class AuthStrategy(ABC):
    """
    Abstract base class for authentication strategies.
    
    Authentication strategies implement the logic for a specific authentication method
    (e.g., session-based, OAuth2 token-based, API key-based). Each strategy is responsible
    for extracting credentials from the request, validating them, and returning user information.
    
    Custom authentication strategies should inherit from this class and implement
    the authenticate method.
    """
    
    @abstractmethod
    async def authenticate(self, request: Request, db: Session) -> Optional[User]:
        """
        Authenticate a request using this strategy.
        
        Args:
            request (Request): The incoming HTTP request
            db (Session): Database session for user lookups
            
        Returns:
            Optional[User]: The authenticated user if authentication succeeds, None otherwise
        """
        pass

class AuthType(str, Enum):
    """
    Enum defining the types of authentication supported by the system.
    
    This classification helps with route configuration and middleware processing,
    allowing routes to specify which authentication methods they accept.
    
    Types:
        NONE: No authentication required (public routes)
        SESSION: Session-based authentication (for UI routes)
        OAUTH2: OAuth2 token-based authentication (for API routes)
        ANY: Any authentication method is acceptable
    """
    NONE = "none"
    SESSION = "session"
    OAUTH2 = "oauth2"
    ANY = "any"

class AuthContext:
    """
    Container for authentication-related information.
    
    This class stores authentication state and user information that is
    attached to the request state and made available to route handlers.
    It includes information about how the user was authenticated, what
    scopes or permissions they have, and other authentication metadata.
    """
    
    def __init__(self, 
                 user: Optional[User] = None, 
                 auth_type: Optional[AuthType] = None,
                 scopes: Optional[List[str]] = None,
                 token: Optional[Dict[str, Any]] = None,
                 **metadata):
        """
        Initialize the authentication context.
        
        Args:
            user (Optional[User]): The authenticated user
            auth_type (Optional[AuthType]): The authentication method used
            scopes (Optional[List[str]]): OAuth2 scopes or permissions granted
            token (Optional[Dict[str, Any]]): Token information if token-based auth is used
            **metadata: Additional authentication metadata
        """
        self.user = user
        self.auth_type = auth_type
        self.scopes = scopes or []
        self.token = token or {}
        self.metadata = metadata
        
    @property
    def is_authenticated(self) -> bool:
        """
        Check if the request is authenticated.
        
        Returns:
            bool: True if the user is authenticated, False otherwise
        """
        return self.user is not None
    
    def has_scope(self, scope: str) -> bool:
        """
        Check if the authenticated user has a specific scope.
        
        Args:
            scope (str): The scope to check for
            
        Returns:
            bool: True if the user has the scope, False otherwise
        """
        return scope in self.scopes

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication across the application.
    
    This middleware evaluates authentication according to multiple strategies,
    loads user information, and attaches it to the request state for use by
    route handlers. It supports different authentication requirements for
    different routes and provides a unified interface for authentication.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        strategies: List[AuthStrategy],
        public_paths: List[str] = None,
        auth_path_mapping: Dict[str, List[AuthType]] = None
    ):
        """
        Initialize the authentication middleware.
        
        Args:
            app (ASGIApp): The ASGI application
            strategies (List[AuthStrategy]): List of authentication strategies to try
            public_paths (List[str], optional): List of paths that require no authentication
            auth_path_mapping (Dict[str, List[AuthType]], optional): Mapping of paths to
                required authentication types
        """
        super().__init__(app)
        self.strategies = strategies
        self.public_paths = public_paths or []
        self.auth_path_mapping = auth_path_mapping or {}
        
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request through the middleware.
        
        This method is called for each request processed by the application.
        It tries each authentication strategy in turn, attaches authentication
        information to the request state, and enforces authentication requirements
        for protected routes.
        
        Args:
            request (Request): The incoming HTTP request
            call_next (RequestResponseEndpoint): The next middleware or route handler
            
        Returns:
            Response: The HTTP response
        """
        # Get database session
        db = next(get_db())
        
        # Initialize auth context with no authentication
        auth_context = AuthContext()
        request.state.auth = auth_context
        
        # Check if path is public
        path = request.url.path
        if self._is_public_path(path):
            logger.debug(f"Path is public: {path}")
            return await call_next(request)
        
        # Try each authentication strategy
        for strategy in self.strategies:
            try:
                user = await strategy.authenticate(request, db)
                if user:
                    # User authenticated, update context
                    strategy_name = strategy.__class__.__name__
                    logger.info(f"User authenticated via {strategy_name}: {user.id}")
                    
                    # Determine auth type based on strategy
                    auth_type = self._get_auth_type_for_strategy(strategy)
                    
                    # Create auth context with authenticated user
                    auth_context = AuthContext(
                        user=user,
                        auth_type=auth_type,
                        # Additional properties set by specific strategies
                    )
                    request.state.auth = auth_context
                    break
            except Exception as e:
                logger.error(f"Error in auth strategy {strategy.__class__.__name__}: {str(e)}")
        
        # Check if authentication is required for this path
        required_auth_types = self._get_required_auth_types(path)
        
        if required_auth_types and not self._is_auth_type_allowed(auth_context.auth_type, required_auth_types):
            # Authentication required but not provided or wrong type
            logger.warning(f"Authentication required for path {path}, got {auth_context.auth_type}")
            
            # Return appropriate error response based on expected auth type
            if AuthType.SESSION in required_auth_types:
                # For session auth, redirect to login page
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/login", status_code=302)
            else:
                # For API auth, return 401 Unauthorized
                return JSONResponse(
                    status_code=401, 
                    content={"detail": "Authentication required"}
                )
        
        # Proceed with the request
        return await call_next(request)
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (requires no authentication).
        
        Args:
            path (str): The request path
            
        Returns:
            bool: True if the path is public, False otherwise
        """
        # Check exact matches first
        if path in self.public_paths:
            return True
        
        # Check path prefixes
        for public_path in self.public_paths:
            if public_path.endswith("*") and path.startswith(public_path[:-1]):
                return True
                
        return False
    
    def _get_required_auth_types(self, path: str) -> List[AuthType]:
        """
        Get the authentication types required for a path.
        
        Args:
            path (str): The request path
            
        Returns:
            List[AuthType]: List of allowed authentication types for the path
        """
        # Check exact matches first
        if path in self.auth_path_mapping:
            return self.auth_path_mapping[path]
        
        # Check path prefixes
        for auth_path, auth_types in self.auth_path_mapping.items():
            if auth_path.endswith("*") and path.startswith(auth_path[:-1]):
                return auth_types
                
        # Default to ANY auth
        return [AuthType.ANY]
    
    def _is_auth_type_allowed(self, auth_type: Optional[AuthType], required_types: List[AuthType]) -> bool:
        """
        Check if an authentication type is allowed for the required types.
        
        Args:
            auth_type (Optional[AuthType]): The actual authentication type
            required_types (List[AuthType]): List of allowed authentication types
            
        Returns:
            bool: True if the authentication type is allowed, False otherwise
        """
        # If NONE is allowed, no authentication is required
        if AuthType.NONE in required_types:
            return True
        
        # If no auth type provided, only allowed if NONE is accepted
        if auth_type is None:
            return False
        
        # ANY means any authentication method is acceptable
        if AuthType.ANY in required_types:
            return auth_type != AuthType.NONE
            
        # Check if the auth type is in the list of required types
        return auth_type in required_types
    
    def _get_auth_type_for_strategy(self, strategy: AuthStrategy) -> AuthType:
        """
        Determine the authentication type for a strategy.
        
        Args:
            strategy (AuthStrategy): The authentication strategy
            
        Returns:
            AuthType: The corresponding authentication type
        """
        # Map strategy class names to auth types
        strategy_class_name = strategy.__class__.__name__
        
        if "Session" in strategy_class_name:
            return AuthType.SESSION
        elif "OAuth" in strategy_class_name:
            return AuthType.OAUTH2
        
        # Default to ANY for custom strategies
        return AuthType.ANY

# Concrete Authentication Strategies

class SessionAuthStrategy(AuthStrategy):
    """
    Session-based authentication strategy.
    
    This strategy checks for a valid session cookie and loads the associated user.
    It's used primarily for UI routes that require an interactive user session.
    """
    
    async def authenticate(self, request: Request, db: Session) -> Optional[User]:
        """
        Authenticate using session information.
        
        Args:
            request (Request): The incoming HTTP request
            db (Session): Database session for user lookups
            
        Returns:
            Optional[User]: The authenticated user if found, None otherwise
        """
        # Check if session exists and contains user_id
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        
        # Lookup user in database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            # Invalid user ID in session, clear it
            request.session.pop("user_id", None)
            return None
            
        return user

class OAuth2AuthStrategy(AuthStrategy):
    """
    OAuth2 token-based authentication strategy.
    
    This strategy checks for a valid OAuth2 token in the Authorization header
    and loads the associated user. It also extracts and validates the token's
    scopes for authorization purposes.
    """
    
    async def authenticate(self, request: Request, db: Session) -> Optional[User]:
        """
        Authenticate using OAuth2 token.
        
        Args:
            request (Request): The incoming HTTP request
            db (Session): Database session for user lookups
            
        Returns:
            Optional[User]: The authenticated user if token is valid, None otherwise
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        token = auth_header.replace("Bearer ", "")
        
        # Import OAuth2Token model and verify
        from models import OAuth2Token
        from datetime import datetime
        
        # Get token from database
        token_record = db.query(OAuth2Token).filter(
            OAuth2Token.access_token == token,
            OAuth2Token.is_active == True
        ).first()
        
        if not token_record:
            logger.warning(f"Invalid or inactive token attempted to be used")
            return None
        
        # Check if token has expired
        if token_record.expires_at and token_record.expires_at < datetime.utcnow():
            logger.warning(f"Expired token attempted to be used")
            return None
            
        # Get user from token
        user = db.query(User).filter(User.id == token_record.user_id).first()
        if not user:
            logger.warning(f"Token references non-existent user: {token_record.user_id}")
            return None
            
        # Add token info to request state
        scopes = token_record.scopes.split() if token_record.scopes else []
        request.state.token = token_record
        request.state.scopes = scopes
        
        return user

# Utility functions

def create_auth_middleware(app: ASGIApp) -> AuthMiddleware:
    """
    Create and configure the authentication middleware.
    
    This function creates an instance of the AuthMiddleware with the appropriate
    authentication strategies and configuration. It's the main entry point for
    adding authentication to the application.
    
    Auth requirements are collected from plugins via the plugin_manager,
    allowing each plugin to specify its own authentication needs.
    
    Args:
        app (ASGIApp): The ASGI application
        
    Returns:
        AuthMiddleware: Configured authentication middleware
    """
    # Create authentication strategies
    strategies = [
        SessionAuthStrategy(),
        OAuth2AuthStrategy()
    ]
    
    # Define public paths that require no authentication
    public_paths = [
        "/",
        "/login",
        "/register",
        "/error",
        "/static/*",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/webauthn/register/begin",
        "/webauthn/register/complete",
        "/webauthn/login/begin",
        "/webauthn/login/complete"
    ]
    
    # Get authentication requirements from plugins via plugin_manager
    from plugin_manager import plugin_manager
    
    # Get auth requirements from plugins
    plugin_auth_requirements = plugin_manager.get_auth_requirements()
    
    # Convert string auth types to AuthType enum
    auth_path_mapping = {}
    for path, auth_strings in plugin_auth_requirements.items():
        auth_types = []
        for auth_str in auth_strings:
            if auth_str.lower() == "session":
                auth_types.append(AuthType.SESSION)
            elif auth_str.lower() == "oauth2":
                auth_types.append(AuthType.OAUTH2)
            elif auth_str.lower() == "none":
                auth_types.append(AuthType.NONE)
            elif auth_str.lower() == "any":
                auth_types.append(AuthType.ANY)
        
        if auth_types:
            auth_path_mapping[path] = auth_types
    
    # Add default auth for core paths if not defined by plugins
    if "/dashboard" not in auth_path_mapping:
        auth_path_mapping["/dashboard"] = [AuthType.SESSION]
    if "/token" not in auth_path_mapping:
        auth_path_mapping["/token"] = [AuthType.SESSION]
    if "/token/*" not in auth_path_mapping:
        auth_path_mapping["/token/*"] = [AuthType.SESSION]
    
    # Log auth requirements for debugging
    logger.info(f"Auth requirements: {auth_path_mapping}")
    
    # Create middleware
    return AuthMiddleware(
        app=app,
        strategies=strategies, 
        public_paths=public_paths,
        auth_path_mapping=auth_path_mapping
    )

# Decorators and dependencies for route handlers

def requires_auth(auth_types: Union[AuthType, List[AuthType]] = AuthType.ANY):
    """
    Decorator to require specific authentication types for a route.
    
    This decorator can be applied to FastAPI route handlers to specify
    which authentication methods are acceptable for the route. It's an
    alternative to configuring authentication requirements in the middleware.
    
    Args:
        auth_types (Union[AuthType, List[AuthType]]): Required authentication type(s)
        
    Returns:
        Callable: Decorator function
    """
    if isinstance(auth_types, AuthType):
        auth_types = [auth_types]
        
    def decorator(func: Callable) -> Callable:
        # Store authentication requirements in function metadata
        setattr(func, "auth_types", auth_types)
        
        # Check if function is a coroutine function
        if inspect.iscoroutinefunction(func):
            async def wrapper(*args, **kwargs):
                # Extract request from args or kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request and "request" in kwargs:
                    request = kwargs["request"]
                
                if not request:
                    raise ValueError("Request object not found in function arguments")
                
                # Check if authenticated
                auth_context = getattr(request.state, "auth", None)
                if not auth_context or not auth_context.is_authenticated:
                    raise ValueError("Authentication required")
                
                # Check if auth type is allowed
                if not any(auth_context.auth_type == t for t in auth_types):
                    raise ValueError(f"Invalid authentication type: {auth_context.auth_type}")
                
                # Proceed with the function
                return await func(*args, **kwargs)
        else:
            def wrapper(*args, **kwargs):
                # Extract request from args or kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request and "request" in kwargs:
                    request = kwargs["request"]
                
                if not request:
                    raise ValueError("Request object not found in function arguments")
                
                # Check if authenticated
                auth_context = getattr(request.state, "auth", None)
                if not auth_context or not auth_context.is_authenticated:
                    raise ValueError("Authentication required")
                
                # Check if auth type is allowed
                if not any(auth_context.auth_type == t for t in auth_types):
                    raise ValueError(f"Invalid authentication type: {auth_context.auth_type}")
                
                # Proceed with the function
                return func(*args, **kwargs)
                
        return wrapper
    
    return decorator

async def get_auth_context(request: Request) -> AuthContext:
    """
    FastAPI dependency for getting the authentication context.
    
    This function can be used as a FastAPI dependency to inject the
    authentication context into route handlers. It provides access
    to the authenticated user, authentication type, and other
    authentication metadata.
    
    Args:
        request (Request): The incoming HTTP request
        
    Returns:
        AuthContext: The authentication context
        
    Example:
        ```python
        @app.get("/profile")
        async def profile(auth: AuthContext = Depends(get_auth_context)):
            return {"user_id": auth.user.id, "username": auth.user.username}
        ```
    """
    auth_context = getattr(request.state, "auth", None)
    if not auth_context:
        auth_context = AuthContext()
        request.state.auth = auth_context
        
    return auth_context

async def requires_scope(request: Request, scope: str):
    """
    FastAPI dependency for requiring a specific OAuth2 scope.
    
    This function can be used as a FastAPI dependency to ensure that
    the authenticated user has a specific OAuth2 scope. It's used for
    fine-grained access control within API routes.
    
    Args:
        request (Request): The incoming HTTP request
        scope (str): The required OAuth2 scope
        
    Returns:
        None
        
    Raises:
        HTTPException: If the user does not have the required scope
        
    Example:
        ```python
        @app.get("/tweets", dependencies=[Depends(requires_scope("tweet.read"))])
        async def get_tweets():
            return {"tweets": [...]}
        ```
    """
    from fastapi import HTTPException
    
    auth_context = getattr(request.state, "auth", None)
    if not auth_context or not auth_context.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    if not auth_context.has_scope(scope):
        raise HTTPException(
            status_code=403, 
            detail=f"Insufficient permissions. Required scope: {scope}"
        )