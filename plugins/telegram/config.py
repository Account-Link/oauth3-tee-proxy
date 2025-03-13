# plugins/telegram/config.py
"""
Configuration for Telegram plugin
"""

from pydantic_settings import BaseSettings
from functools import lru_cache

class TelegramSettings(BaseSettings):
    """
    Telegram-specific settings
    
    These settings can be configured via environment variables
    prefixed with TELEGRAM_, e.g., TELEGRAM_API_ID
    """
    # Telegram API credentials - defaults for development only
    API_ID: str = "12345"  # Replace with actual API ID in production
    API_HASH: str = "abcdef1234567890abcdef1234567890"  # Replace with actual API hash in production
    
    # Optional settings
    SESSION_PATH: str = "./telegram_sessions"
    
    # Scopes
    ALLOWED_SCOPES: str = "telegram.post_any telegram.post_specific telegram.read"
    
    class Config:
        env_prefix = "TELEGRAM_"
        env_file = ".env"

@lru_cache()
def get_telegram_settings():
    """
    Get the Telegram settings, cached to avoid reloading
    """
    return TelegramSettings()