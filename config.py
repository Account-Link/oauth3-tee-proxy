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

    # Telegram Settings
    TELEGRAM_API_ID: str
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_PATH: str = "./telegram_sessions"

    # OAuth2 Settings
    OAUTH2_TOKEN_EXPIRE_HOURS: int = 24
    OAUTH2_ALLOWED_SCOPES: str = "telegram.post_any tweet.post twitter_oauth1.auth twitter_oauth1.tweet"
    
    # Twitter OAuth Settings
    TWITTER_CONSUMER_KEY: str = ""
    TWITTER_CONSUMER_SECRET: str = ""
    TWITTER_OAUTH_CALLBACK_URL: str = "http://localhost:8000/auth/twitter/callback"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 