# plugins/twitter/resource/__init__.py
"""
Twitter Resource Plugins
======================

This package contains resource plugins for Twitter, providing access to
Twitter resources and functionality in the OAuth3 TEE Proxy.

The package includes different resource server implementations:
- API resource server: Handles interaction with Twitter API (tweets, etc.)

Each resource plugin implements the ResourcePlugin interface defined in
the plugins module, providing a consistent way to interact with Twitter.
"""

from .api import TwitterApiResourcePlugin