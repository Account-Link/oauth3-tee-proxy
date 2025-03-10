# plugins/telegram/__init__.py
"""
Telegram Plugin Package for OAuth3 TEE Proxy
===========================================

This package provides Telegram integration for the OAuth3 TEE Proxy,
enabling users to authenticate with Telegram and perform Telegram operations
through the TEE Proxy.

The package includes:
- TelegramAuthorizationPlugin: Handles Telegram authentication using Telethon
- TelegramResourcePlugin: Handles Telegram API operations (messages, channels, etc.)

Both plugins are automatically registered with the plugin system when this
package is imported. The plugins implement the standard interfaces defined
in the plugins module, providing a consistent way to interact with Telegram.

Authentication Flow:
------------------
1. User initiates Telegram authentication with their phone number
2. The TelegramAuthorizationPlugin requests a verification code from Telegram
3. User receives the code and submits it to the TEE Proxy
4. The plugin validates the code and creates a session
5. The session is stored securely in the TEE Proxy database
6. Clients can request OAuth2 tokens from the TEE Proxy to access Telegram

Supported Operations:
------------------
- Sending messages to channels
- Listing available channels
- Reading messages (planned)

Supported Scopes:
---------------
- telegram.post_any: Permission to post to any Telegram channel
- telegram.post_specific: Permission to post to specific Telegram channels
- telegram.read: Permission to read Telegram messages
"""

from .auth import TelegramAuthorizationPlugin
from .resource import TelegramResourcePlugin

# Register plugins
from plugins import register_authorization_plugin, register_resource_plugin

# Automatically register the plugins when this package is imported
register_authorization_plugin(TelegramAuthorizationPlugin)
register_resource_plugin(TelegramResourcePlugin)