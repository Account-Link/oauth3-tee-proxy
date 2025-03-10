# plugins/twitter/__init__.py
"""
Twitter Plugin Package for OAuth3 TEE Proxy
===========================================

This package provides Twitter integration for the OAuth3 TEE Proxy,
enabling users to authenticate with Twitter and perform Twitter operations
through the TEE Proxy.

The package includes:
- TwitterAuthorizationPlugin: Handles Twitter authentication using cookies
- TwitterResourcePlugin: Handles Twitter API operations (tweets, etc.)

Both plugins are automatically registered with the plugin system when this
package is imported. The plugins implement the standard interfaces defined
in the plugins module, providing a consistent way to interact with Twitter.

Authentication Flow:
------------------
1. User submits their Twitter cookie to the TEE Proxy
2. The TwitterAuthorizationPlugin validates the cookie and extracts the user ID
3. The cookie is stored securely in the TEE Proxy database
4. Clients can request OAuth2 tokens from the TEE Proxy to access Twitter

Supported Operations:
------------------
- Posting tweets
- Reading tweets (planned)
- Deleting tweets (planned)

Supported Scopes:
---------------
- tweet.post: Permission to post tweets
- tweet.read: Permission to read tweets
- tweet.delete: Permission to delete tweets
"""

from .auth import TwitterAuthorizationPlugin
from .resource import TwitterResourcePlugin

# Register plugins
from plugins import register_authorization_plugin, register_resource_plugin

# Automatically register the plugins when this package is imported
register_authorization_plugin(TwitterAuthorizationPlugin)
register_resource_plugin(TwitterResourcePlugin)