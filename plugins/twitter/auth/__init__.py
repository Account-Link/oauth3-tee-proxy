# plugins/twitter/auth/__init__.py
"""
Twitter Authorization Plugins
============================

This package contains authorization plugins for Twitter, providing authentication
mechanisms for Twitter integration in the OAuth3 TEE Proxy.

The package includes different authorization mechanisms:
- Cookie-based authentication: Handles Twitter authentication using browser cookies

Each authorization plugin implements the AuthorizationPlugin interface defined in
the plugins module, providing a consistent way to authenticate with Twitter.
"""

from .cookie import TwitterCookieAuthorizationPlugin