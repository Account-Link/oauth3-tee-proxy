# plugins/telegram/resource.py
"""
Telegram Resource Plugin for OAuth3 TEE Proxy
===========================================

This module implements the Telegram resource plugin for the OAuth3 TEE Proxy.
It handles interaction with the Telegram API on behalf of users, providing
functionality for sending messages to Telegram channels and other operations.

The TelegramResourcePlugin class implements the ResourcePlugin interface,
providing methods for:
- Initializing Telegram API clients with user credentials
- Validating Telegram API clients
- Defining available scopes for Telegram operations
- Sending messages to Telegram channels

The plugin uses the TelegramClient wrapper class that encapsulates the
interaction with the Telethon library, providing a simplified interface for
common operations and handling errors in a consistent way.

Supported Scopes:
---------------
- telegram.post_any: Permission to post to any Telegram channel
- telegram.post_specific: Permission to post to specific Telegram channels
- telegram.read: Permission to read Telegram messages
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
    """
    Telegram client wrapper used by the resource plugin.
    
    This class wraps the Telethon TelegramClient class, providing a simplified
    interface for interacting with the Telegram API. It handles connection management,
    error handling, and provides async-compatible methods for common Telegram operations.
    
    The TelegramClient is created by the TelegramResourcePlugin using the credentials
    stored in the database. It is responsible for making API calls to Telegram and
    handling the responses.
    
    Attributes:
        client (TelethonClient): The underlying Telethon client used for API calls
        _is_connected (bool): Flag indicating whether the client is connected to Telegram
    """
    
    def __init__(self, client: TelethonClient):
        """
        Initialize with a Telethon client.
        
        Args:
            client (TelethonClient): The Telethon client to wrap
        """
        self.client = client
        self._is_connected = False
    
    async def connect(self):
        """
        Connect to Telegram if not already connected.
        
        Establishes a connection to the Telegram servers if one is not already
        established. Sets the _is_connected flag to True on successful connection.
        """
        if not self._is_connected:
            await self.client.connect()
            self._is_connected = True
    
    async def disconnect(self):
        """
        Disconnect from Telegram if connected.
        
        Closes the connection to the Telegram servers if one is established.
        Sets the _is_connected flag to False.
        """
        if self._is_connected:
            await self.client.disconnect()
            self._is_connected = False
    
    async def __aenter__(self):
        """
        Async context manager entry point.
        
        Connects to Telegram when entering the context and returns the client.
        Allows using the client with the 'async with' statement.
        
        Returns:
            TelegramClient: The client itself
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit point.
        
        Disconnects from Telegram when exiting the context.
        Allows using the client with the 'async with' statement.
        """
        await self.disconnect()
    
    async def validate(self) -> bool:
        """
        Validate if the client is still working.
        
        Makes a lightweight API call to Telegram to check if the client's credentials
        are still valid. Returns True if the call succeeds, False otherwise.
        
        Returns:
            bool: True if the client is valid, False otherwise
        """
        try:
            await self.connect()
            me = await self.client.get_me()
            return me is not None
        except Exception as e:
            logger.error(f"Error validating Telegram client: {e}")
            return False
            
    async def send_message(self, chat_id: str, message: str) -> int:
        """
        Send a message to a chat and return the message ID.
        
        Sends a message to the specified chat or channel and returns the ID
        of the sent message. The chat_id can be a channel ID, a username,
        or a phone number.
        
        Args:
            chat_id (str): The ID or username of the chat to send the message to
            message (str): The text of the message to send
            
        Returns:
            int: The ID of the sent message
            
        Raises:
            Exception: If sending the message fails
        """
        try:
            await self.connect()
            result = await self.client.send_message(int(chat_id), message)
            return result.id
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            raise
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """
        Get list of channels the user has access to.
        
        Retrieves a list of all channels and supergroups the user is a member of.
        Returns a list of dictionaries containing channel information.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries with channel information:
                - id: The channel ID
                - name: The channel name
                - username: The channel username (if available)
                - participants_count: The number of participants (if available)
                
        Raises:
            Exception: If fetching the channels fails
        """
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
    """
    Plugin for Telegram resource operations.
    
    This class implements the ResourcePlugin interface for Telegram operations,
    providing methods for initializing Telegram clients, validating clients,
    and performing operations like sending messages to channels.
    
    The plugin defines the available scopes for Telegram operations and provides
    methods for working with these scopes. It serves as a bridge between the
    OAuth3 TEE Proxy and the Telegram API.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("telegram")
        SCOPES (Dict[str, str]): Dictionary mapping scope names to descriptions
        
    Attributes:
        api_id (int): The Telegram API ID from application settings
        api_hash (str): The Telegram API hash from application settings
    """
    
    service_name = "telegram"
    
    SCOPES = {
        "telegram.post_any": "Permission to post to any Telegram channel",
        "telegram.post_specific": "Permission to post to specific Telegram channels",
        "telegram.read": "Permission to read Telegram messages",
    }
    
    def __init__(self):
        """
        Initialize the Telegram resource plugin.
        
        Retrieves the Telegram API ID and hash from application settings and
        initializes the plugin with these credentials. These credentials are
        used for all Telegram API interactions.
        """
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TelegramClient:
        """
        Initialize Telegram client with credentials.
        
        Creates a new TelegramClient instance using the provided credentials.
        This method is called by the TEE Proxy when it needs to make Telegram
        API calls on behalf of a user.
        
        Args:
            credentials (Dict[str, Any]): The Telegram credentials, must include 'session_string'
            
        Returns:
            TelegramClient: An initialized Telegram client
            
        Raises:
            ValueError: If the session string is missing from the credentials
            Exception: If the client cannot be initialized
        """
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
        """
        Validate if the Telegram client is still valid.
        
        Checks if the Telegram client's credentials are still valid by making
        a lightweight API call to Telegram.
        
        Args:
            client (TelegramClient): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
        """
        return await client.validate()
    
    def get_available_scopes(self) -> List[str]:
        """
        Get the list of scopes supported by this resource plugin.
        
        Returns the list of scope names that can be requested for Telegram
        operations. These scopes define the permissions that clients can
        request when accessing Telegram resources.
        
        Returns:
            List[str]: List of scope strings
        """
        return list(self.SCOPES.keys())
    
    async def send_message(self, client: TelegramClient, chat_id: str, message: str) -> int:
        """
        Send a message using the client.
        
        Sends a message to the specified chat or channel using the provided
        TelegramClient. This method is called by the TEE Proxy when a client with
        appropriate permissions requests to send a message.
        
        Args:
            client (TelegramClient): The Telegram client to use
            chat_id (str): The ID or username of the chat to send the message to
            message (str): The text of the message to send
            
        Returns:
            int: The ID of the sent message
            
        Raises:
            Exception: If sending the message fails
        """
        return await client.send_message(chat_id, message)
    
    async def get_channels(self, client: TelegramClient) -> List[Dict[str, Any]]:
        """
        Get channels available to the client.
        
        Retrieves a list of all channels and supergroups the user is a member of.
        This method is called by the TEE Proxy when a client with appropriate
        permissions requests to list available channels.
        
        Args:
            client (TelegramClient): The Telegram client to use
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with channel information
            
        Raises:
            Exception: If fetching the channels fails
        """
        return await client.get_channels()