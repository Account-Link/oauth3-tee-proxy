# plugins/telegram/auth.py
"""
Telegram authorization plugin for OAuth3 TEE Proxy.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple

from plugins import AuthorizationPlugin
from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class TelegramAuthorizationPlugin(AuthorizationPlugin):
    """Plugin for Telegram authentication using Telethon."""
    
    service_name = "telegram"
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate if the Telegram session is still valid."""
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
        """Get Telegram user ID or phone number from the credentials."""
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
        Request verification code for phone number
        Returns: Dict with phone_code_hash and session_string
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
        Sign in with the verification code
        Returns: Dict with user info and session string
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
        """Convert credentials dictionary to a JSON string."""
        return json.dumps(credentials)
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """Convert JSON string to credentials dictionary."""
        try:
            return json.loads(credentials_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Telegram credentials: {e}")
            raise ValueError("Invalid Telegram credentials format") from e