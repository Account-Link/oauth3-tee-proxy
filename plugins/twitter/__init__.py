# plugins/twitter/__init__.py
"""
Twitter plugin for OAuth3 TEE Proxy.
"""

from .auth import TwitterAuthorizationPlugin
from .resource import TwitterResourcePlugin

# Register plugins
from plugins import register_authorization_plugin, register_resource_plugin

register_authorization_plugin(TwitterAuthorizationPlugin)
register_resource_plugin(TwitterResourcePlugin)