# plugins/telegram/auth.py
"""
Telegram Authorization Plugin for OAuth3 TEE Proxy
================================================

This module implements the Telegram authorization plugin for the OAuth3 TEE Proxy.
It handles authentication with Telegram using the Telethon library, allowing
users to link their Telegram accounts to the TEE Proxy.

The TelegramAuthorizationPlugin class implements the AuthorizationPlugin interface,
providing methods for:
- Validating Telegram sessions
- Extracting Telegram user IDs from sessions
- Converting Telegram sessions between string and dictionary formats
- Handling the phone verification code flow for Telegram authentication

This plugin uses the Telethon library to interact with the Telegram API, providing
a straightforward way to authenticate users and perform operations on their behalf.

Authentication Flow:
------------------
1. User initiates the Telegram authentication process
2. The plugin requests a verification code for the user's phone number
3. User receives the code and submits it to the plugin
4. The plugin verifies the code and creates a session
5. The session is stored in the database, linked to the user's account
6. The TEE Proxy can now make Telegram API calls on behalf of the user
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple

from plugins import AuthorizationPlugin
from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from plugins.telegram.config import get_telegram_settings

settings = get_telegram_settings()
logger = logging.getLogger(__name__)

class TelegramAuthorizationPlugin(AuthorizationPlugin):
    """
    Plugin for Telegram authentication using Telethon.
    
    This class implements the AuthorizationPlugin interface for Telegram authentication
    using the Telethon library. It provides functionality for validating Telegram sessions,
    extracting user IDs, and handling the phone verification code flow.
    
    The plugin uses the Telethon library to interact with the Telegram API, providing
    a secure way to authenticate users and perform operations on their behalf.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("telegram")
    
    Attributes:
        api_id (int): The Telegram API ID from application settings
        api_hash (str): The Telegram API hash from application settings
    """
    
    def get_plugin_id(self) -> str:
        """
        Get the unique identifier for this authorization plugin.
        
        Returns:
            str: The plugin ID ("telegram")
        """
        return "telegram"
    
    def get_display_name(self) -> str:
        """
        Get a human-readable name for this authorization method.
        
        Returns:
            str: The display name ("Telegram Authentication")
        """
        return "Telegram Authentication"
    
    service_name = "telegram"
    
    def __init__(self):
        """
        Initialize the Telegram authorization plugin.
        
        Retrieves the Telegram API ID and hash from application settings and
        initializes the plugin with these credentials. These credentials are
        used for all Telegram API interactions.
        """
        self.api_id = settings.API_ID
        self.api_hash = settings.API_HASH
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the Telegram session is still valid.
        
        Attempts to connect to Telegram using the session string in the credentials
        and retrieves the user's information. Returns True if the connection and
        retrieval are successful, indicating that the session is still valid.
        
        Args:
            credentials (Dict[str, Any]): Dictionary containing Telegram credentials,
                                         must include 'session_string'
            
        Returns:
            bool: True if the session is valid, False otherwise
            
        Note:
            This method catches all exceptions and returns False for any error,
            logging the error for debugging purposes.
        """
        try:
            session_string = credentials.get('session_string')
            if not session_string:
                return False
                
            async with TelethonClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            ) as client:
                me = await client.get_me()
                return me is not None
        except Exception as e:
            logger.error(f"Error validating Telegram session: {e}")
            return False
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Get Telegram user ID or phone number from the credentials.
        
        Extracts the user identifier from the credentials. If a session string
        is available, connects to Telegram and retrieves the user ID. Otherwise,
        returns the phone number from the credentials.
        
        Args:
            credentials (Dict[str, Any]): Dictionary containing Telegram credentials
            
        Returns:
            str: The Telegram user ID if available, otherwise the phone number
            
        Raises:
            Exception: If retrieving the user ID fails
        """
        try:
            session_string = credentials.get('session_string')
            if not session_string:
                # Return phone number if no session string is available
                return credentials.get('phone_number', '')
                
            async with TelethonClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            ) as client:
                me = await client.get_me()
                return str(me.id)
        except Exception as e:
            logger.error(f"Error getting Telegram user ID: {e}")
            raise
    
    async def request_verification_code(self, phone_number: str) -> Dict[str, str]:
        """
        Request a verification code for a phone number.
        
        Initiates the Telegram authentication flow by requesting a verification
        code for the given phone number. The code will be sent to the user via
        Telegram or SMS, depending on Telegram's policy.
        
        Args:
            phone_number (str): The phone number to request a code for, in international format
            
        Returns:
            Dict[str, str]: Dictionary containing:
                - phone_code_hash: The hash needed for code verification
                - session_string: The session string for this authentication attempt
                - phone_number: The phone number the code was sent to
            
        Raises:
            Exception: If requesting the verification code fails
        """
        client = TelethonClient(StringSession(), self.api_id, self.api_hash)
        try:
            await client.connect()
            sent = await client.send_code_request(phone_number)
            return {
                "phone_code_hash": sent.phone_code_hash,
                "session_string": client.session.save(),
                "phone_number": phone_number
            }
        except Exception as e:
            logger.error(f"Error requesting verification code: {e}")
            raise
        finally:
            await client.disconnect()
    
    async def sign_in(
        self, 
        phone_number: str, 
        code: str, 
        phone_code_hash: str, 
        session_string: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sign in with a verification code.
        
        Completes the Telegram authentication flow by verifying the code sent to
        the user's phone. If the account has two-factor authentication enabled,
        the password parameter must be provided.
        
        Args:
            phone_number (str): The phone number in international format
            code (str): The verification code received by the user
            phone_code_hash (str): The hash returned from request_verification_code
            session_string (str): The session string from request_verification_code
            password (Optional[str]): The two-factor authentication password, if enabled
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - user_id: The Telegram user ID
                - phone_number: The phone number used for authentication
                - session_string: The session string for future API calls
            
        Raises:
            ValueError: If the code is invalid or 2FA is enabled but no password is provided
            Exception: If sign-in fails for any other reason
        """
        client = TelethonClient(
            StringSession(session_string),
            self.api_id,
            self.api_hash
        )
        
        try:
            await client.connect()
            
            try:
                user = await client.sign_in(
                    phone=phone_number,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
            except SessionPasswordNeededError:
                if not password:
                    raise ValueError("Two-factor authentication is enabled. Password required.")
                user = await client.sign_in(password=password)
            
            credentials = {
                "user_id": str(user.id),
                "phone_number": phone_number,
                "session_string": client.session.save()
            }
            
            return credentials
            
        except PhoneCodeInvalidError:
            raise ValueError("Invalid verification code")
        except Exception as e:
            logger.error(f"Error during sign in: {e}")
            raise
        finally:
            await client.disconnect()
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials dictionary to a JSON string.
        
        Serializes the Telegram credentials dictionary to a JSON string
        for storage in the database.
        
        Args:
            credentials (Dict[str, Any]): The Telegram credentials
            
        Returns:
            str: The JSON string representation of the credentials
        """
        return json.dumps(credentials)
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """
        Convert JSON string to credentials dictionary.
        
        Deserializes a JSON string representation of Telegram credentials
        back into a dictionary that can be used by the plugin.
        
        Args:
            credentials_str (str): The JSON string representation of the credentials
            
        Returns:
            Dict[str, Any]: The deserialized Telegram credentials
            
        Raises:
            ValueError: If the string cannot be parsed as JSON
        """
        try:
            return json.loads(credentials_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Telegram credentials: {e}")
            raise ValueError("Invalid Telegram credentials format") from e