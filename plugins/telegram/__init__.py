# plugins/telegram/__init__.py
"""
Telegram plugin for OAuth3 TEE Proxy.
"""

from .auth import TelegramAuthorizationPlugin
from .resource import TelegramResourcePlugin

# Register plugins
from plugins import register_authorization_plugin, register_resource_plugin

register_authorization_plugin(TelegramAuthorizationPlugin)
register_resource_plugin(TelegramResourcePlugin)