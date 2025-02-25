from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///oauth3.db"
    
    # Session Management
    SESSION_EXPIRY_HOURS: int = 24
    SESSION_COOKIE_NAME: str = "oauth3_session"
    SESSION_SAME_SITE: str = "lax"
    SESSION_HTTPS_ONLY: bool = False  # Set to True in production
    
    # Post Key Settings
    POST_KEY_MAX_PER_ACCOUNT: int = 5
    
    # Safety Filter Settings
    SAFETY_FILTER_ENABLED: bool = True
    SAFETY_FILTER_MAX_TOKENS: int = 280
    
    # WebAuthn settings
    WEBAUTHN_RP_ID: str = "localhost"  # Change this to your domain in production
    WEBAUTHN_RP_NAME: str = "OAuth3 Twitter Cookie"
    WEBAUTHN_ORIGIN: str = "http://localhost:8000"  # Change this to your origin in production
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production!

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 