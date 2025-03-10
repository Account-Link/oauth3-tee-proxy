# plugins/telegram/resource.py
"""
Telegram resource plugin for OAuth3 TEE Proxy.
"""

import logging
from typing import Dict, Any, List, Optional

from plugins import ResourcePlugin
from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class TelegramClient:
    """Telegram client wrapper used by the resource plugin."""
    
    def __init__(self, client: TelethonClient):
        """Initialize with a Telethon client."""
        self.client = client
        self._is_connected = False
    
    async def connect(self):
        """Connect to Telegram if not already connected."""
        if not self._is_connected:
            await self.client.connect()
            self._is_connected = True
    
    async def disconnect(self):
        """Disconnect from Telegram if connected."""
        if self._is_connected:
            await self.client.disconnect()
            self._is_connected = False
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def validate(self) -> bool:
        """Validate if the client is still working."""
        try:
            await self.connect()
            me = await self.client.get_me()
            return me is not None
        except Exception as e:
            logger.error(f"Error validating Telegram client: {e}")
            return False
            
    async def send_message(self, chat_id: str, message: str) -> int:
        """Send a message to a chat and return the message ID."""
        try:
            await self.connect()
            result = await self.client.send_message(int(chat_id), message)
            return result.id
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            raise
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels the user has access to."""
        try:
            await self.connect()
            channels = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel:
                    channels.append({
                        "id": str(dialog.id),
                        "name": dialog.name,
                        "username": dialog.entity.username if hasattr(dialog.entity, "username") else None,
                        "participants_count": dialog.entity.participants_count if hasattr(dialog.entity, "participants_count") else None
                    })
            return channels
        except Exception as e:
            logger.error(f"Error fetching Telegram channels: {e}")
            raise

class TelegramResourcePlugin(ResourcePlugin):
    """Plugin for Telegram resource operations."""
    
    service_name = "telegram"
    
    SCOPES = {
        "telegram.post_any": "Permission to post to any Telegram channel",
        "telegram.post_specific": "Permission to post to specific Telegram channels",
        "telegram.read": "Permission to read Telegram messages",
    }
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TelegramClient:
        """Initialize Telegram client with credentials."""
        try:
            session_string = credentials.get('session_string')
            if not session_string:
                raise ValueError("Missing session string in credentials")
                
            client = TelethonClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
            
            return TelegramClient(client)
        except Exception as e:
            logger.error(f"Error initializing Telegram client: {e}")
            raise
    
    async def validate_client(self, client: TelegramClient) -> bool:
        """Validate if the Telegram client is still valid."""
        return await client.validate()
    
    def get_available_scopes(self) -> List[str]:
        """Get the list of scopes supported by this resource plugin."""
        return list(self.SCOPES.keys())
    
    async def send_message(self, client: TelegramClient, chat_id: str, message: str) -> int:
        """Send a message using the client."""
        return await client.send_message(chat_id, message)
    
    async def get_channels(self, client: TelegramClient) -> List[Dict[str, Any]]:
        """Get channels available to the client."""
        return await client.get_channels()