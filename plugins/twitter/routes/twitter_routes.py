"""
Twitter Route Definitions
=======================

This module implements the FastAPI routes for Twitter functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
interact with Twitter via the proxy.

The TwitterRoutes class implements the RoutePlugin interface and provides
routes for:
- Twitter API interactions
- Policy management

This module no longer contains authentication or account management routes,
which have been moved to more specialized modules.
"""

import logging

from fastapi import APIRouter

from plugins import RoutePlugin

# Import the route modules
from .auth_ui import create_auth_ui_router
from .cookie_routes import create_cookie_auth_router
from .account_routes import create_account_router

logger = logging.getLogger(__name__)

class TwitterRoutes(RoutePlugin):
    """
    Twitter route plugin that provides endpoints for interacting with Twitter.
    
    This plugin implements the RoutePlugin interface and registers routes for
    Twitter-specific functionality, including:
    - Twitter API interactions (tweets, etc.)
    - Policy management
    """
    
    service_name = "twitter"
    
    def get_router(self) -> APIRouter:
        """
        Get the router for this plugin's routes.
        
        This is required by the RoutePlugin interface.
        
        Returns:
            APIRouter: FastAPI router with all plugin-specific routes
        """
        return self.create_routes()
    
    def create_routes(self) -> APIRouter:
        """
        Create and return an API router with Twitter routes.
        
        This method sets up all the HTTP endpoints for Twitter functionality
        and returns them as a FastAPI APIRouter that can be included in the
        main app.
        
        Returns:
            APIRouter: FastAPI router with Twitter-specific routes
        """
        router = APIRouter(tags=["twitter"])
        
        # Include the auth routes with appropriate prefixes
        auth_ui_router = create_auth_ui_router()
        router.include_router(auth_ui_router, prefix="/auth/admin")
        
        cookie_auth_router = create_cookie_auth_router()
        router.include_router(cookie_auth_router, prefix="/auth/cookies")
        
        # Include the account routes with appropriate prefix
        account_router = create_account_router()
        router.include_router(account_router, prefix="/accounts")
        
        return router