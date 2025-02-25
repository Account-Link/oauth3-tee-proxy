from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from typing import Optional, List, Dict
import logging
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class TelegramClient:
    def __init__(self, session_string: Optional[str] = None):
        """Initialize Telegram client with optional session string"""
        self.client = TelethonClient(
            StringSession(session_string) if session_string else StringSession(),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
    
    async def __aenter__(self):
        await self.client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()
    
    async def request_verification_code(self, phone_number: str) -> Dict[str, str]:
        """
        Request verification code for phone number
        Returns: Dict with phone_code_hash and session_string
        """
        try:
            sent = await self.client.send_code_request(phone_number)
            return {
                "phone_code_hash": sent.phone_code_hash,
                "session_string": self.client.session.save()
            }
        except Exception as e:
            logger.error(f"Error requesting verification code: {str(e)}")
            raise
    
    async def sign_in(self, phone_number: str, code: str, phone_code_hash: str, password: Optional[str] = None) -> Dict:
        """
        Sign in with the verification code
        Returns: Dict with user info and session string
        """
        try:
            try:
                user = await self.client.sign_in(
                    phone=phone_number,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
            except SessionPasswordNeededError:
                if not password:
                    raise ValueError("Two-factor authentication is enabled. Password required.")
                user = await self.client.sign_in(password=password)
            
            return {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "phone": user.phone,
                "session_string": self.client.session.save()
            }
        except PhoneCodeInvalidError:
            raise ValueError("Invalid verification code")
        except Exception as e:
            logger.error(f"Error during sign in: {str(e)}")
            raise
    
    async def get_channels(self) -> List[Dict]:
        """Get list of channels the user has access to"""
        try:
            channels = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel:
                    channels.append({
                        "id": str(dialog.id),  # Convert to string for JSON safety
                        "name": dialog.name,
                        "username": dialog.entity.username if hasattr(dialog.entity, "username") else None,
                        "participants_count": dialog.entity.participants_count if hasattr(dialog.entity, "participants_count") else None
                    })
            return channels
        except Exception as e:
            logger.error(f"Error fetching channels: {str(e)}")
            raise
    
    async def validate_session(self) -> bool:
        """Validate if the current session is still valid"""
        try:
            me = await self.client.get_me()
            return me is not None
        except Exception:
            return False
