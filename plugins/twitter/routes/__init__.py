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

from .twitter_routes import TwitterRoutes
from .graphql_routes import TwitterGraphQLRoutes
from .v1_routes import TwitterV1Routes
from .oauth_routes import TwitterOAuthRoutes

# This makes it easier to import the routes in one go
__all__ = ['TwitterRoutes', 'TwitterGraphQLRoutes', 'TwitterV1Routes', 'TwitterOAuthRoutes']