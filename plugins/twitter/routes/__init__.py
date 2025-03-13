# plugins/twitter/routes/__init__.py
"""
Twitter Routes for OAuth3 TEE Proxy
=================================

This package provides FastAPI route definitions for Twitter endpoints
in the OAuth3 TEE Proxy.

The routes handle HTTP interactions related to Twitter functionality,
such as linking Twitter accounts and posting tweets. They are separate
from both authorization and resource access concerns, focusing purely
on HTTP interface definitions.

Routes are grouped by functionality and include:
- Account routes: Endpoints for linking and managing Twitter accounts
- OAuth routes: Endpoints for Twitter OAuth authentication and account linking
- Tweet routes: Endpoints for posting and managing tweets
- GraphQL routes: Endpoints for interacting with Twitter's GraphQL API
- v1.1 API routes: Endpoints for interacting with Twitter's v1.1 REST API

All routes are mounted under the "/twitter" prefix in the main application.
"""

# Import the main route classes
from .twitter_routes import TwitterRoutes
from .graphql_routes import TwitterGraphQLRoutes
from .v1_routes import TwitterV1Routes
from .oauth_routes import TwitterOAuthRoutes

# Import modular route factories
from .account_routes import create_account_router
from .auth_ui import create_auth_ui_router
from .cookie_routes import create_cookie_auth_router

# This makes it easier to import the routes in one go
__all__ = [
    # Main route classes
    'TwitterRoutes', 'TwitterGraphQLRoutes', 'TwitterV1Routes', 'TwitterOAuthRoutes',
    
    # Modular route factories
    'create_account_router', 'create_auth_ui_router', 'create_cookie_auth_router'
]