# plugins/twitter/resource/__init__.py
"""
Twitter Resource Plugins
======================

This package contains resource plugins for Twitter, providing access to
Twitter resources and functionality in the OAuth3 TEE Proxy.

The package includes different resource server implementations:
- API resource server: Handles interaction with Twitter API (tweets, etc.)
- GraphQL resource server: Handles interaction with Twitter's GraphQL API
- v1.1 API resource server: Handles interaction with Twitter's v1.1 REST API

Each resource plugin implements the ResourcePlugin interface defined in
the plugins module, providing a consistent way to interact with Twitter.
"""

from .api import TwitterApiResourcePlugin
from .v1 import TwitterV1ResourcePlugin