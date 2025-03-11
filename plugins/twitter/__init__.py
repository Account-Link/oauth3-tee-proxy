# plugins/twitter/__init__.py
"""
Twitter Plugin Package for OAuth3 TEE Proxy
===========================================

This package provides Twitter integration for the OAuth3 TEE Proxy,
enabling users to authenticate with Twitter and perform Twitter operations
through the TEE Proxy.

The package implements a clear separation between authorization servers, resource servers, and routes:

Authorization Servers:
--------------------
- TwitterCookieAuthorizationPlugin: Handles Twitter authentication using browser cookies

Resource Servers:
---------------
- TwitterApiResourcePlugin: Handles Twitter API operations (tweets, etc.)
- TwitterGraphQLResourcePlugin: Provides passthrough access to Twitter's private GraphQL API

Routes:
------
- TwitterRoutes: Provides HTTP endpoints for Twitter functionality
- TwitterGraphQLRoutes: Provides HTTP endpoints for Twitter's GraphQL API

All plugins are automatically registered with the plugin system when this
package is imported. The plugins implement the standard interfaces defined
in the plugins module, providing a consistent way to interact with Twitter.

Authentication Flow:
------------------
1. User submits their Twitter cookie to the TEE Proxy via an HTTP endpoint
2. The Authorization Server validates the cookie and extracts the user ID
3. The cookie is stored securely in the TEE Proxy database
4. Clients can request OAuth2 tokens from the TEE Proxy to access Twitter resources

Supported Operations:
------------------
- Posting tweets
- Reading tweets (planned)
- Deleting tweets (planned)
- GraphQL API access (all operations supported as passthrough)

Supported Scopes:
---------------
- tweet.post: Permission to post tweets
- tweet.read: Permission to read tweets
- tweet.delete: Permission to delete tweets
- twitter.graphql: Permission to make GraphQL API calls to Twitter
- twitter.graphql.read: Permission to make read-only GraphQL API calls
- twitter.graphql.write: Permission to make write GraphQL API calls
"""

# Import Authorization Servers
from .auth.cookie import TwitterCookieAuthorizationPlugin

# Import Resource Servers
from .resource.api import TwitterApiResourcePlugin
from .resource.graphql import TwitterGraphQLResourcePlugin

# Import Routes
from .routes import TwitterRoutes, TwitterGraphQLRoutes

# Register plugins
from plugins import register_authorization_plugin, register_resource_plugin, register_route_plugin

# Automatically register the plugins when this package is imported
register_authorization_plugin(TwitterCookieAuthorizationPlugin)
register_resource_plugin(TwitterApiResourcePlugin)
register_resource_plugin(TwitterGraphQLResourcePlugin)
register_route_plugin(TwitterRoutes)
register_route_plugin(TwitterGraphQLRoutes)

# Apply patches to the Twitter library
from .patches import apply_patches
apply_patches()